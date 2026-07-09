import { useState, useEffect } from 'react';

export function useHealth() {
  const [status, setStatus] = useState<string>('unknown');

  useEffect(() => {
    // Placeholder for periodic health checking
    setStatus('healthy');
  }, []);

  return { status };
}
