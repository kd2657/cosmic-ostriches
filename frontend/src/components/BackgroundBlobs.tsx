"use client";

import { useEffect, useRef } from "react";

/**
 * BackgroundBlobs: Animated ambient background layer.
 *
 * Renders five floating color blobs with organic trigonometric trajectories
 * and a mouse-repulsion physics field. A separate mask layer reveals a
 * floating-vector grid effect that tracks the cursor.
 * Fully RAF-driven — bypasses React's render loop for smooth 60fps animation.
 */
export default function BackgroundBlobs() {
  const blobRefs = useRef<(HTMLDivElement | null)[]>([]);
  const vectorRefs = useRef<(HTMLDivElement | null)[]>([]);
  const maskLayerRef = useRef<HTMLDivElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0, active: false });

  useEffect(() => {
    mouseRef.current.x = window.innerWidth / 2;
    mouseRef.current.y = window.innerHeight / 2;

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY, active: true };
    };
    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);
    window.addEventListener("blur", handleMouseLeave);

    let animationFrameId: number;
    const blobs = [
      { id: 1, color: "bg-blue-600/20",   cx: 0.2, cy: 0.2, r: 250, speed: 0.0010, offset: 0 },
      { id: 2, color: "bg-purple-600/20", cx: 0.8, cy: 0.8, r: 350, speed: 0.0007, offset: 2 },
      { id: 3, color: "bg-pink-600/20",   cx: 0.8, cy: 0.3, r: 200, speed: 0.0015, offset: 4 },
      { id: 4, color: "bg-teal-600/20",   cx: 0.2, cy: 0.8, r: 250, speed: 0.0011, offset: 5 },
      { id: 5, color: "bg-indigo-600/20", cx: 0.5, cy: 0.5, r: 400, speed: 0.0008, offset: 1 },
    ];
    const vectors = Array.from({ length: 40 }).map((_, i) => ({
      id: i + 1,
      cx: 0.05 + Math.random() * 0.9,
      cy: 0.05 + Math.random() * 0.9,
      speed: 0.0003 + Math.random() * 0.0005,
      offset: Math.random() * Math.PI * 2,
      text: `[${(Math.random() * 2 - 1).toFixed(3)}, ${(Math.random() * 2 - 1).toFixed(3)}]`,
    }));

    vectorRefs.current.forEach((el, index) => {
      if (el && vectors[index]) {
        el.textContent = vectors[index].text;
      }
    });

    const currentPositions = blobs.map((b) => ({
      x: b.cx * window.innerWidth,
      y: b.cy * window.innerHeight,
    }));
    const vectorPositions = vectors.map((v) => ({
      x: v.cx * window.innerWidth,
      y: v.cy * window.innerHeight,
    }));

    let maskX = mouseRef.current.x;
    let maskY = mouseRef.current.y;
    let maskO = 0;

    const animate = (time: number) => {
      blobRefs.current.forEach((el, index) => {
        if (!el) return;
        const b = blobs[index];
        const w = window.innerWidth;
        const h = window.innerHeight;

        // Idle organic trigonometric floating trajectory
        const floatX = b.cx * w + Math.sin(time * b.speed + b.offset) * 150;
        const floatY = b.cy * h + Math.cos(time * b.speed + b.offset) * 150;

        let targetX = floatX;
        let targetY = floatY;

        // Dynamic mouse repulsion field (inverse distance pushing)
        if (mouseRef.current.active) {
          const dx = floatX - mouseRef.current.x;
          const dy = floatY - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 450 && dist > 1) {
            const force = (450 - dist) / 450;
            const pushFactor = force * 350;
            targetX += (dx / dist) * pushFactor;
            targetY += (dy / dist) * pushFactor;
          }
        }

        // Smooth lerp so blobs glide instead of teleporting
        currentPositions[index].x += (targetX - currentPositions[index].x) * 0.04;
        currentPositions[index].y += (targetY - currentPositions[index].y) * 0.04;

        el.style.transform = `translate(${currentPositions[index].x - b.r}px, ${currentPositions[index].y - b.r}px)`;
      });

      vectorRefs.current.forEach((el, index) => {
        if (!el || !vectors[index]) return;
        const v = vectors[index];
        const w = window.innerWidth;
        const h = window.innerHeight;
        const floatX = v.cx * w + Math.sin(time * v.speed * 1.2 + v.offset) * 40;
        const floatY = v.cy * h + Math.cos(time * v.speed * 1.2 + v.offset) * 40;
        vectorPositions[index].x += (floatX - vectorPositions[index].x) * 0.02;
        vectorPositions[index].y += (floatY - vectorPositions[index].y) * 0.02;
        el.style.transform = `translate(${vectorPositions[index].x}px, ${vectorPositions[index].y}px)`;
      });

      maskX += (mouseRef.current.x - maskX) * 0.1;
      maskY += (mouseRef.current.y - maskY) * 0.1;
      maskO += ((mouseRef.current.active ? 1 : 0) - maskO) * 0.05;

      if (maskLayerRef.current) {
        maskLayerRef.current.style.opacity = maskO.toString();
        const maskGrad = `radial-gradient(circle 600px at ${maskX}px ${maskY}px, black 0%, transparent 100%)`;
        maskLayerRef.current.style.setProperty("-webkit-mask-image", maskGrad);
        maskLayerRef.current.style.setProperty("mask-image", maskGrad);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("blur", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
      <div
        ref={maskLayerRef}
        className="absolute inset-0 z-10 pointer-events-none transition-opacity duration-300"
        style={{ opacity: 0 }}
      >
        <div
          className="absolute inset-0 z-0 opacity-[0.08]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255, 255, 255, 1) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 1) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        {Array.from({ length: 40 }).map((_, i) => (
          <div
            key={`vec-${i}`}
            ref={(el) => {
              if (el) vectorRefs.current[i] = el;
            }}
            className="absolute top-0 left-0 text-neutral-700/60 font-mono text-[10px] sm:text-xs tracking-widest whitespace-nowrap transition-none will-change-transform font-bold"
          />
        ))}
      </div>

      {[
        { id: 1, color: "bg-blue-600/20",   r: 250 },
        { id: 2, color: "bg-purple-600/20", r: 350 },
        { id: 3, color: "bg-pink-600/20",   r: 200 },
        { id: 4, color: "bg-teal-600/20",   r: 250 },
        { id: 5, color: "bg-indigo-600/20", r: 400 },
      ].map((b, i) => (
        <div
          key={b.id}
          ref={(el) => {
            if (el) blobRefs.current[i] = el;
          }}
          className={`absolute top-0 left-0 rounded-full blur-[100px] ${b.color} transition-none will-change-transform`}
          style={{ width: b.r * 2, height: b.r * 2 }}
        />
      ))}
    </div>
  );
}
