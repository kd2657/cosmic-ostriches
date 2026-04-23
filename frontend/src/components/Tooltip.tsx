"use client";

import React, { useState, useRef, useEffect } from 'react';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * A high-fidelity, premium Tooltip component that replaces native 'title' attributes.
 * Designed for cosmic-ostriches with backdrop blur and smooth animations.
 */
export default function Tooltip({ content, children, className = "" }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const updatePosition = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords({
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height + 10
      });
    }
  };

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
      updatePosition();
    }, 1000);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  };

  useEffect(() => {
    if (isVisible) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, { passive: true });
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [isVisible]);

  return (
    <div 
      ref={triggerRef}
      className={`relative inline-flex items-center cursor-help ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {isVisible && (
        <div 
          className="fixed z-[1000] px-3 py-2 bg-neutral-900/95 backdrop-blur-xl border border-neutral-800/80 text-neutral-200 text-[12px] font-medium rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.5)] animate-in fade-in zoom-in-95 duration-200 pointer-events-none -translate-x-1/2 whitespace-normal max-w-[240px] leading-relaxed text-center"
          style={{ 
            left: `${coords.x}px`, 
            top: `${coords.y}px` 
          }}
        >
          {content}
          {/* Subtle Pointer Arrow */}
          <div className="absolute -top-[5px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-neutral-900 border-t border-l border-neutral-800/80 rotate-45" />
        </div>
      )}
    </div>
  );
}
