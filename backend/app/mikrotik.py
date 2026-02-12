import aiohttp
import codecs
import random
import string
import ipaddress
from typing import Optional, Set, Dict, List, Any
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

class MikrotikAPI:
    def __init__(self, host: str, username: str, password: str, 
                 port: Optional[int] = None, use_ssl: bool = True, verify_ssl: bool = False):
        protocol = "https" if use_ssl else "http"
        self.base_url = f"{protocol}://{host}"
        if port:
            self.base_url += f":{port}"
        self.base_url += "/rest"
        self.auth = aiohttp.BasicAuth(username, password)
        self.ssl_ctx = False if (use_ssl and not verify_ssl) else None
        self.host = host

    async def request(self, method: str, endpoint: str, payload: dict = None) -> Any:
        url = self.base_url + endpoint
        print(f"\n🔵 MIKROTIK REQUEST: {method} {url}")
        if payload:
            print(f"🔵 PAYLOAD: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, json=payload,
                auth=self.auth, ssl=self.ssl_ctx, timeout=15
            ) as resp:
                text = await resp.text()
                print(f"🟡 MIKROTIK RESPONSE STATUS: {resp.status}")
                print(f"🟡 MIKROTIK RESPONSE BODY: {text[:500]}")
                
                try:
                    data = await resp.json()
                except:
                    data = None
                
                if resp.status >= 400:
                    raise Exception(f"MikroTik API Error {resp.status}: {text}")
                
                if data and isinstance(data, dict):
                    if "error" in data:
                        raise Exception(f"MikroTik API Error {data.get('error')}: {data.get('message', text)}")
                    if "detail" in data and "error" in str(data["detail"]).lower():
                        raise Exception(f"MikroTik API Error: {data['detail']}")
                
                if data is not None:
                    return data
                return {"success": True, "raw": text}

    async def get_identity(self) -> dict:
        return await self.request("GET", "/system/identity")

    async def get_wireguard_peers(self) -> List[dict]:
        result = await self.request("GET", "/interface/wireguard/peers")
        return result if isinstance(result, list) else []

    async def get_wireguard_interfaces(self) -> List[dict]:
        result = await self.request("GET", "/interface/wireguard")
        return result if isinstance(result, list) else []

class MikrotikResourceManager:
    def __init__(self, api: MikrotikAPI):
        self.api = api

    async def get_used_ips(self) -> Set[str]:
        used = set()
        addrs = await self.api.request("GET", "/ip/address")
        if isinstance(addrs, list):
            for item in addrs:
                addr = item.get("address", "")
                if "/" in addr:
                    used.add(addr.split("/")[0])
                if item.get("network"):
                    used.add(item["network"])
        
        peers = await self.api.get_wireguard_peers()
        for p in peers:
            allowed = p.get("allowed-address", "")
            for entry in allowed.split(","):
                if "/" in entry:
                    used.add(entry.split("/")[0])
        return used

    async def get_used_ports(self) -> Set[int]:
        used = set()
        rules = await self.api.request("GET", "/ip/firewall/nat?chain=dstnat")
        if isinstance(rules, list):
            for rule in rules:
                port = rule.get("dst-port", "")
                if "-" in port:
                    try:
                        start, end = map(int, port.split("-"))
                        used.update(range(start, end + 1))
                    except:
                        pass
                elif port.isdigit():
                    used.add(int(port))
        return used

    async def get_next_free_ip(self, subnet: str) -> str:
        used = await self.get_used_ips()
        network = ipaddress.ip_network(subnet)
        gateway = str(network.network_address + 1)
        
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str != gateway and ip_str not in used:
                return ip_str
        raise Exception("IP pool exhausted")

    async def get_free_port_block(self, start: int = 20000, count: int = 4) -> int:
        used = await self.get_used_ports()
        candidate = start
        while candidate < 60000:
            if all((candidate + i) not in used for i in range(count)):
                return candidate
            candidate += 1
        raise Exception("No free port block")

class WireGuardManager:
    SERVICES = {
        "dapodik": 5774,
        "erapor_sd": 8535,
        "erapor_smp": 8534,
        "https": 443,
    }

    def __init__(self, api: MikrotikAPI, resource_mgr: MikrotikResourceManager):
        self.api = api
        self.res = resource_mgr

    @staticmethod
    def generate_keys() -> tuple[str, str]:
        priv = X25519PrivateKey.generate()
        pub = priv.public_key()
        
        priv_bytes = priv.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption()
        )
        pub_bytes = pub.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw
        )
        
        priv_b64 = codecs.encode(priv_bytes, 'base64').decode().strip()
        pub_b64 = codecs.encode(pub_bytes, 'base64').decode().strip()
        return priv_b64, pub_b64

    async def provision(self, client_name: str, pool_subnet: str, 
                       enable_nat: bool, duration_days: int) -> Dict[str, Any]:
        srv_priv, srv_pub = self.generate_keys()
        cli_priv, cli_pub = self.generate_keys()
        
        client_ip = await self.res.get_next_free_ip(pool_subnet)
        srv_port = random.randint(13000, 19000)
        
        network = ipaddress.ip_network(pool_subnet)
        gateway_ip = str(network.network_address + 1)
        
        # Unique interface name (avoids MikroTik conflicts)
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        iface_name = f"wg_{client_name}_{suffix}"
        
        exp_str = "UNLIMITED"
        if duration_days > 0:
            exp_date = datetime.now() + timedelta(days=duration_days)
            exp_str = exp_date.strftime("%Y-%m-%d")
        
        comment = f"Client: {client_name} | EXP: {exp_str}"
        
        iface = await self.api.request("PUT", "/interface/wireguard", {
            "name": iface_name,
            "private-key": srv_priv,
            "listen-port": str(srv_port),
            "mtu": "1420",
            "comment": comment,
        })
        
        if not iface or '.id' not in iface:
            raise Exception("Failed to create interface")
        
        try:
            await self.api.request("PUT", "/ip/address", {
                "interface": iface_name,
                "address": f"{gateway_ip}/32",
                "network": client_ip,
            })
            
            peer = await self.api.request("PUT", "/interface/wireguard/peers", {
                "interface": iface_name,
                "public-key": cli_pub,
                "allowed-address": f"{client_ip}/32",
                "persistent-keepalive": "25s",
                "comment": comment,
            })
            
            peer_id = peer.get('.id') if peer else None
            
            nat_mappings = {}
            if enable_nat:
                base_port = await self.res.get_free_port_block()
                
                for i, (svc, internal_port) in enumerate(self.SERVICES.items()):
                    pub_port = base_port + i
                    await self.api.request("PUT", "/ip/firewall/nat", {
                        "chain": "dstnat",
                        "protocol": "tcp",
                        "dst-address": self.api.host,
                        "dst-port": str(pub_port),
                        "action": "dst-nat",
                        "to-addresses": client_ip,
                        "to-ports": str(internal_port),
                        "comment": f"{iface_name}_{svc}",
                    })
                    nat_mappings[svc] = pub_port
                
                await self.api.request("PUT", "/ip/firewall/nat", {
                    "chain": "srcnat",
                    "action": "masquerade",
                    "out-interface": iface_name,
                    "comment": f"Masq-{client_name}",
                })
            
            if duration_days > 0:
                # Use same suffix from interface name for unique scheduler name
                suffix = iface_name.split('_')[-1]  # extract 't91b' from 'wg_my-device_t91b'
                await self._create_scheduler(client_name, duration_days, comment, suffix)
            
            return {
                "client_name": client_name,
                "client_ip": client_ip,
                "gateway_ip": gateway_ip,
                "server_public_key": srv_pub,
                "server_endpoint": self.api.host,
                "server_port": srv_port,
                "client_private_key": cli_priv,
                "interface_name": iface_name,
                "mikrotik_peer_id": peer_id,
                "nat_mappings": nat_mappings if enable_nat else None,
                "expires_at": exp_str if duration_days > 0 else None,
            }
            
        except Exception as e:
            await self.api.request("DELETE", f"/interface/wireguard/{iface['.id']}")
            raise

    async def _create_scheduler(self, client_name: str, days: int, comment: str, suffix: str):
        expire = datetime.now() + timedelta(days=days)
        sched_name = f"EXP_{client_name}_{suffix}"  # ✅ unique name
        
        script = f'''
    /interface wireguard peers disable [find comment="{comment}"]
    /log warning "WireGuard expired: {client_name}"
    /system scheduler remove [find name="{sched_name}"]
    '''
        
        await self.api.request("PUT", "/system/scheduler", {
            "name": sched_name,
            "start-date": expire.strftime("%b/%d/%Y"),
            "start-time": expire.strftime("%H:%M:%S"),
            "interval": "0s",
            "on-event": script,
        })

    async def get_client_stats(self, interface_name: str) -> Optional[Dict]:
        peers = await self.api.get_wireguard_peers()
        for peer in peers:
            if peer.get("interface") == interface_name:
                last_handshake = peer.get("last-handshake")
                return {
                    "last_handshake": last_handshake if last_handshake != "never" else None,
                    "rx_bytes": int(peer.get("rx", 0)),
                    "tx_bytes": int(peer.get("tx", 0)),
                    "enabled": not peer.get("disabled", False),
                }
        return None

    async def delete_client(self, interface_name: str):
        """Completely remove client and all associated resources from MikroTik."""
        
        # 1. Delete IP address assigned to this interface
        try:
            addrs = await self.api.request("GET", f"/ip/address?interface={interface_name}")
            if isinstance(addrs, list):
                for addr in addrs:
                    if addr.get('.id'):
                        await self.api.request("DELETE", f"/ip/address/{addr['.id']}")
                        print(f"✅ Deleted IP address {addr.get('address')} from {interface_name}")
        except Exception as e:
            print(f"⚠️ Failed to delete IP address for {interface_name}: {e}")

        # 2. Delete NAT rules (dstnat and srcnat) with comment containing interface name
        try:
            rules = await self.api.request("GET", f"/ip/firewall/nat?comment~{interface_name}")
            if isinstance(rules, list):
                for rule in rules:
                    if rule.get('.id'):
                        await self.api.request("DELETE", f"/ip/firewall/nat/{rule['.id']}")
                        print(f"✅ Deleted NAT rule {rule.get('comment')}")
        except Exception as e:
            print(f"⚠️ Failed to delete NAT rules for {interface_name}: {e}")

        # 3. Delete scheduler (if any)
        try:
            # Extract base name from interface: "wg_my-device_t91b" -> "my-device_t91b"
            base_name = interface_name[3:]  # remove "wg_"
            scheds = await self.api.request("GET", f"/system/scheduler?name~EXP_{base_name}")
            if isinstance(scheds, list):
                for s in scheds:
                    if s.get('.id'):
                        await self.api.request("DELETE", f"/system/scheduler/{s['.id']}")
                        print(f"✅ Deleted scheduler {s.get('name')}")
        except Exception as e:
            print(f"⚠️ Failed to delete scheduler for {interface_name}: {e}")

        # 4. Delete WireGuard interface
        try:
            ifaces = await self.api.request("GET", f"/interface/wireguard?name={interface_name}")
            if isinstance(ifaces, list) and ifaces:
                iface_id = ifaces[0]['.id']
                await self.api.request("DELETE", f"/interface/wireguard/{iface_id}")
                print(f"✅ Deleted WireGuard interface {interface_name}")
        except Exception as e:
            print(f"⚠️ Failed to delete interface {interface_name}: {e}")
            raise  # re-raise because interface deletion is critical