import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { usePointer } from '../hooks/usePointer';

export type OrbState = 'idle' | 'listening' | 'working' | 'speaking' | 'blocked';

interface OrbProps {
  state: OrbState;
}

export const Orb: React.FC<OrbProps> = ({ state }) => {
  const pointer = usePointer();

  // Magnetic parallax effect calculations
  // Orb is roughly at window.innerWidth - 100, window.innerHeight - 100
  const magneticPull = useMemo(() => {
    const orbX = window.innerWidth - 80;
    const orbY = window.innerHeight - 80;
    const dx = pointer.x - orbX;
    const dy = pointer.y - orbY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // If within 300px, apply magnetic pull
    if (distance < 300) {
      const pull = Math.max(0, 300 - distance) / 300; // 0 to 1
      return { x: dx * pull * 0.15, y: dy * pull * 0.15 };
    }
    return { x: 0, y: 0 };
  }, [pointer.x, pointer.y]);

  // Procedural Liquid Orb Configurations (border-radius trick)
  const variants: Variants = {
    idle: {
      scale: 1,
      borderRadius: ["50% 50% 50% 50%", "45% 55% 45% 55%", "50% 50% 50% 50%"],
      rotate: 360,
      boxShadow: '0 0 15px rgba(255, 255, 255, 0.2)',
      backgroundColor: 'rgba(255, 255, 255, 0.8)',
      transition: { duration: 10, repeat: Infinity, ease: 'linear' }
    },
    listening: {
      scale: 1.1,
      borderRadius: ["40% 60% 70% 30%", "60% 40% 30% 70%", "40% 60% 70% 30%"],
      rotate: 360,
      boxShadow: '0 0 30px rgba(59, 130, 246, 0.6)',
      backgroundColor: 'rgba(96, 165, 250, 0.9)',
      transition: { duration: 3, repeat: Infinity, ease: 'linear' }
    },
    working: {
      scale: 1.05,
      borderRadius: ["30% 70% 70% 30%", "70% 30% 30% 70%", "30% 70% 70% 30%"],
      rotate: -360,
      boxShadow: '0 0 40px rgba(167, 139, 250, 0.8)',
      backgroundColor: 'rgba(196, 181, 253, 0.9)',
      transition: { duration: 2, repeat: Infinity, ease: 'linear' }
    },
    speaking: {
      scale: [1.15, 1.25, 1.15],
      borderRadius: ["30% 70% 50% 50%", "50% 50% 30% 70%", "70% 30% 50% 50%", "30% 70% 50% 50%"],
      rotate: 360,
      boxShadow: '0 0 50px rgba(52, 211, 153, 0.9)',
      backgroundColor: 'rgba(110, 231, 183, 1)',
      transition: { duration: 0.5, repeat: Infinity, ease: 'linear' }
    },
    blocked: {
      scale: 1,
      borderRadius: "50%",
      boxShadow: '0 0 20px rgba(239, 68, 68, 0.6)',
      backgroundColor: 'rgba(248, 113, 113, 0.9)',
      transition: { duration: 0.5 }
    }
  };

  return (
    <motion.div 
      className="fixed bottom-8 right-8 z-50 flex items-center justify-center w-24 h-24"
      animate={{ x: magneticPull.x, y: magneticPull.y }}
      transition={{ type: 'spring', stiffness: 150, damping: 15, mass: 0.5 }}
    >
      <motion.div
        className="w-16 h-16 backdrop-blur-md border border-white/20"
        variants={variants}
        animate={state}
        initial="idle"
      />
    </motion.div>
  );
};
