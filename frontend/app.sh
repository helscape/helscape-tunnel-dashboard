cat > app/layout.tsx << 'EOF'
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VPN Pro · Glass Dashboard",
  description: "Minimalist flat glassmorphism",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"
        />
      </head>
      <body className="flex items-center justify-center min-h-screen p-4 md:p-8">
        <div className="glass w-full max-w-7xl p-6 md:p-8">
          {children}
        </div>
      </body>
    </html>
  );
}
EOF
