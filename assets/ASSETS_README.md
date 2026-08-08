# Asset Groundwork

This folder holds all media assets needed for the visual overlay.

## Directory Structure
- `/icons`: SVG icons for the floating glass cards, control panel, etc.
- `/animations`: Lottie files or pre-rendered sprite sheets for complex motions if not using programmatic CSS/Canvas.

## Design vs. Code
- **The Orb**: Should be implemented programmatically using the Web Audio API (AnalyserNode) driving a WebGL/Canvas shader (e.g., Three.js metaballs) to allow true real-time morphing based on audio amplitude. Do NOT pre-render the orb as a video/gif.
- **Glass Cards**: Implement purely via CSS (backdrop-filter: blur) and Tailwind.
- **Icons**: Standardize on an open-source set like Lucide React.
