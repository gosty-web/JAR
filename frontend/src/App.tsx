import { useState, useEffect } from 'react';
import { Orb } from './components/Orb';
import { GlassCard } from './components/GlassCard';
import { MouseTrail } from './components/MouseTrail';
import { ConstellationView } from './components/ConstellationView';
import { useWebSocket } from './hooks/useWebSocket';
import { useSound } from './hooks/useSound';
import './styles/globals.css';

function App() {
  const { orbState, isConnected, thought, confidence } = useWebSocket('ws://localhost:8000/ws');
  const { playSound } = useSound();
  const [fullAccess, setFullAccess] = useState(false);

  // Trigger sound on state change
  useEffect(() => {
    if (orbState === 'listening') playSound('notification');
    else if (orbState === 'working') playSound('stateChange');
    else if (orbState === 'blocked') playSound('error');
    else if (orbState === 'speaking') playSound('success');
  }, [orbState, playSound]);

  // Determine edge glow color based on orb state
  const edgeGlowClass = 
    orbState === 'listening' ? 'shadow-[inset_0_0_100px_rgba(59,130,246,0.3)]' :
    orbState === 'working' ? 'shadow-[inset_0_0_100px_rgba(167,139,250,0.3)]' :
    orbState === 'blocked' ? 'shadow-[inset_0_0_100px_rgba(239,68,68,0.4)]' :
    orbState === 'speaking' ? 'shadow-[inset_0_0_100px_rgba(52,211,153,0.3)]' : '';

  // Interactive layer logic:
  // If we wanted to show floating cards or interactive elements, we would
  // wrap them in a div with the `interactive-layer` class so they receive clicks.
  
  return (
    <div className={`w-screen h-screen transition-all duration-1000 ${edgeGlowClass}`}>
      <MouseTrail />
      {/* 
        The root div is click-through by default due to pointer-events: none in globals.css.
        Interactive layers must specify pointer-events: auto.
      */}
      <Orb state={isConnected ? orbState : 'blocked'} />
      
      {/* Left-side Control Panel */}
      <div className="fixed top-8 left-8 flex flex-col gap-4 interactive-layer">
        <ConstellationView />
        <div className="glass rounded-xl p-4 flex items-center justify-between w-80">
          <span className="text-white/80 text-sm font-medium tracking-wide">FULL ACCESS MODE</span>
          <button 
            onClick={() => setFullAccess(!fullAccess)}
            className={`w-12 h-6 rounded-full transition-colors duration-300 relative ${fullAccess ? 'bg-red-500/80' : 'bg-white/20'}`}
          >
            <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all duration-300 ${fullAccess ? 'left-7' : 'left-1'}`} />
          </button>
        </div>
      </div>

      <GlassCard 
        visible={!!thought && isConnected} 
        title="Reasoning" 
        content={thought || ''} 
        confidence={confidence} 
      />
    </div>
  );
}

export default App;
