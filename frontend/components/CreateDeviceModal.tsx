'use client';

import { useState, useEffect } from 'react';

interface CreateDeviceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (deviceName: string) => void;
  isCreating: boolean;
}

export default function CreateDeviceModal({
  isOpen,
  onClose,
  onCreate,
  isCreating,
}: CreateDeviceModalProps) {
  const [deviceName, setDeviceName] = useState('');
  const [error, setError] = useState('');

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setDeviceName('');
      setError('');
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const trimmed = deviceName.trim();
    if (!trimmed) {
      setError('Device name is required');
      return;
    }

    // Allow only letters, numbers, dash, underscore
    const sanitized = trimmed.replace(/[^a-zA-Z0-9_-]/g, '');
    if (!sanitized) {
      setError('Only letters, numbers, dash (-) and underscore (_) are allowed');
      return;
    }

    if (sanitized !== trimmed) {
      setError('Special characters are not allowed (only a-z, 0-9, -, _)');
      return;
    }

    onCreate(sanitized);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="glass w-full max-w-md p-6 animate-in fade-in zoom-in duration-200">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium flex items-center gap-2">
            <i className="fas fa-plus-circle"></i> Create New Device
          </h3>
          <button
            onClick={onClose}
            className="btn btn-sm !px-3 !py-1"
            disabled={isCreating}
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-xs opacity-70 mb-1">
              Device Name
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="e.g., my-laptop, office-pc"
              value={deviceName}
              onChange={(e) => {
                setDeviceName(e.target.value);
                setError('');
              }}
              autoFocus
              disabled={isCreating}
              maxLength={32}
            />
            {error && (
              <p className="text-xs text-red-400 mt-1">{error}</p>
            )}
            <p className="text-xs opacity-50 mt-2">
              Only letters, numbers, dash (-) and underscore (_). Max 32 characters.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn flex-1"
              disabled={isCreating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary flex-1"
              disabled={isCreating}
            >
              {isCreating ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-1"></i>
                  Creating...
                </>
              ) : (
                'Create Device'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}