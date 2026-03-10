"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

interface ImageViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  src: string;
  downloadFilename?: string;
}

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 3;
const ZOOM_STEP = 0.25;

export function ImageViewerModal({
  isOpen,
  onClose,
  src,
  downloadFilename = "generated.png",
}: ImageViewerModalProps) {
  const [zoom, setZoom] = useState(1);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) modalRef.current?.focus();
  }, [isOpen]);

  const zoomIn = useCallback(() => {
    setZoom((z) => Math.min(ZOOM_MAX, z + ZOOM_STEP));
  }, []);
  const zoomOut = useCallback(() => {
    setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_STEP));
  }, []);

  useEffect(() => {
    if (!isOpen) setZoom(1);
  }, [isOpen]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") onClose();
      if (e.key === "+" || e.key === "=") zoomIn();
      if (e.key === "-") zoomOut();
    },
    [isOpen, onClose, zoomIn, zoomOut]
  );

  if (!isOpen) return null;

  return (
    <>
      <div
        className="modal-overlay image-viewer-overlay"
        onClick={onClose}
        onKeyDown={handleKeyDown}
        aria-hidden="true"
        role="presentation"
      />
      <div
        className="image-viewer-modal"
        role="dialog"
        aria-label="Image viewer"
        ref={modalRef}
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        <div className="image-viewer-toolbar">
          <div className="image-viewer-zoom">
            <button
              type="button"
              onClick={zoomOut}
              aria-label="Zoom out"
              disabled={zoom <= ZOOM_MIN}
            >
              −
            </button>
            <span className="image-viewer-zoom-val">{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={zoomIn} aria-label="Zoom in" disabled={zoom >= ZOOM_MAX}>
              +
            </button>
          </div>
          <div className="image-viewer-actions">
            <a href={src} download={downloadFilename} className="image-viewer-download">
              ↓ Download
            </a>
            <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
              ×
            </button>
          </div>
        </div>
        <div className="image-viewer-content" onClick={(e) => e.stopPropagation()}>
          <img src={src} alt="" style={{ transform: `scale(${zoom})` }} draggable={false} />
        </div>
      </div>
    </>
  );
}
