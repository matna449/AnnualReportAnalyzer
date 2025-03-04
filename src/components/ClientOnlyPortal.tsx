'use client';

import React, { useState, useEffect } from 'react';

interface ClientOnlyPortalProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * A component that only renders its children on the client-side
 * to prevent hydration mismatches with components that generate dynamic IDs
 * like Material UI form controls.
 */
const ClientOnlyPortal: React.FC<ClientOnlyPortalProps> = ({ 
  children, 
  fallback = <div style={{ visibility: 'hidden' }}>Loading...</div> 
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return fallback;
  }

  return <>{children}</>;
};

export default ClientOnlyPortal; 