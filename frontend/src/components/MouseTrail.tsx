import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export const MouseTrail: React.FC = () => {
  const [trail, setTrail] = useState<{ x: number; y: number; id: number }[]>([]);

  useEffect(() => {
    let idCounter = 0;
    
    const handleMouseMove = (e: MouseEvent) => {
      const newDot = { x: e.clientX, y: e.clientY, id: idCounter++ };
      setTrail((prev) => [...prev.slice(-15), newDot]);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <>
      {trail.map((dot, index) => (
        <motion.div
          key={dot.id}
          className="fixed w-1.5 h-1.5 bg-white/40 rounded-full pointer-events-none z-40"
          initial={{ opacity: 0.8, scale: 1, x: dot.x, y: dot.y }}
          animate={{ opacity: 0, scale: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ left: -3, top: -3 }}
        />
      ))}
    </>
  );
};
