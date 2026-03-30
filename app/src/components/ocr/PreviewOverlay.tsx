import * as React from 'react';
import type { OcrBox } from '@/lib/types';

interface Props {
  imageUrl: string;
  boxes?: Pick<OcrBox, 'x' | 'y' | 'w' | 'h'>[];
}

export default function PreviewOverlay({ imageUrl, boxes }: Props) {
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const [imgSize, setImgSize] = React.useState<{ w: number; h: number } | null>(null);

  React.useEffect(() => {
    const image = new Image();
    image.onload = () => {
      setImgSize({ w: image.width, h: image.height });
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = image.width;
      canvas.height = image.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      if (boxes && boxes.length) {
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'red';
        boxes.forEach((b) => {
          ctx.strokeRect(b.x, b.y, b.w, b.h);
        });
      }
    };
    image.src = imageUrl;
  }, [imageUrl, boxes]);

  // Render canvas scaled to container width while preserving aspect ratio via CSS
  return (
    <div className="w-full overflow-auto">
      <canvas ref={canvasRef} className="max-w-full h-auto border rounded" />
    </div>
  );
}

