import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface GlassCardProps {
  title?: string;
  content: string;
  visible: boolean;
  confidence?: number; // 0 to 1
}

export const GlassCard: React.FC<GlassCardProps> = ({ title, content, visible, confidence }) => {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          className="fixed bottom-32 right-8 z-40 w-80 interactive-layer"
        >
          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/40 backdrop-blur-xl shadow-2xl p-5 text-left text-white font-sans">
            {/* Subtle top glare */}
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/30 to-transparent" />
            
            {title && (
              <h3 className="text-sm font-semibold tracking-wide text-white/70 mb-2 uppercase">
                {title}
              </h3>
            )}
            
            <p className="text-base font-light leading-relaxed text-white/90">
              {content}
            </p>

            {confidence !== undefined && (
              <div className="mt-4 flex items-center space-x-3">
                <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <motion.div 
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round(confidence * 100)}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
                <span className="text-xs font-mono text-white/50">
                  {Math.round(confidence * 100)}%
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
