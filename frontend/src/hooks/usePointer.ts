import { useEffect, useState } from 'react';

interface PointerState {
  x: number;
  y: number;
}

export const usePointer = (): PointerState => {
  const [pointer, setPointer] = useState<PointerState>({ x: window.innerWidth / 2, y: window.innerHeight / 2 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setPointer({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return pointer;
};
