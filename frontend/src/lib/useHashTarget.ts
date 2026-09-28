import { useEffect } from 'react';
import { useLocation } from 'react-router';

// Hash targets may not exist until an API-backed page finishes loading.
export function useHashTarget(ready: boolean) {
  const { hash } = useLocation();
  let target = hash.slice(1);
  try { target = decodeURIComponent(target); } catch { /* Keep malformed hashes harmless. */ }
  useEffect(() => {
    if (ready && target) document.getElementById(target)?.scrollIntoView({ block: 'start' });
  }, [ready, target]);
  return target;
}
