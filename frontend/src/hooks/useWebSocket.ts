import { useState, useEffect, useRef } from 'react';

type OrbState = 'idle' | 'listening' | 'working' | 'speaking' | 'blocked';

export function useWebSocket(url: string) {
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [thought, setThought] = useState<string | undefined>();
  const [confidence, setConfidence] = useState<number | undefined>();
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to JAR core');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_change') {
            setOrbState(data.state as OrbState);
            if (data.thought) setThought(data.thought);
            if (data.confidence !== undefined) setConfidence(data.confidence);
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect after 2 seconds
        setTimeout(connect, 2000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close();
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  return { orbState, isConnected, thought, confidence };
}
