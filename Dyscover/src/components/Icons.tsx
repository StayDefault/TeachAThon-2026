/** Inline stroke icons (24×24). Decorative by default (aria-hidden). */
import type { SVGProps } from 'react';

type P = SVGProps<SVGSVGElement> & { size?: number };

function Base({ size = 20, children, ...rest }: P) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconSidebar = (p: P) => (
  <Base {...p}>
    <rect x="3" y="4" width="18" height="16" rx="3" />
    <path d="M9 4v16" />
  </Base>
);
export const IconKeyboard = (p: P) => (
  <Base {...p}>
    <rect x="2" y="6" width="20" height="12" rx="2.5" />
    <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10" />
  </Base>
);
export const IconArrowRight = (p: P) => (
  <Base strokeWidth={2.2} {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Base>
);
export const IconPlus = (p: P) => (
  <Base strokeWidth={2.2} {...p}>
    <path d="M12 5v14M5 12h14" />
  </Base>
);
export const IconMinus = (p: P) => (
  <Base strokeWidth={2.2} {...p}>
    <path d="M5 12h14" />
  </Base>
);
export const IconFit = (p: P) => (
  <Base {...p}>
    <path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" />
  </Base>
);
export const IconArrange = (p: P) => (
  <Base {...p}>
    <rect x="2" y="9" width="5" height="6" rx="1" />
    <rect x="16" y="3" width="6" height="6" rx="1" />
    <rect x="16" y="15" width="6" height="6" rx="1" />
    <path d="M7 12h4V6h5M11 12v6h5" />
  </Base>
);
export const IconClose = (p: P) => (
  <Base strokeWidth={2.2} {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Base>
);
export const IconBox = (p: P) => (
  <Base strokeWidth={1.8} {...p}>
    <path d="M21 8l-9-5-9 5 9 5 9-5z" />
    <path d="M3 8v8l9 5 9-5V8M12 13v8" />
  </Base>
);
export const IconFile = (p: P) => (
  <Base {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
  </Base>
);
export const IconImage = (p: P) => (
  <Base {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2.5" />
    <circle cx="9" cy="10" r="2" />
    <path d="M21 17l-5-5-9 8" />
  </Base>
);
export const IconPencil = (p: P) => (
  <Base strokeWidth={2.2} {...p}>
    <path d="M4 20h4L19 9l-4-4L4 16z" />
  </Base>
);
export const IconPlay = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5l11 7-11 7z" />
  </svg>
);
export const IconChart = (p: P) => (
  <Base {...p}>
    <path d="M4 19V5M4 19h16M8 15l4-4 3 3 5-6" />
  </Base>
);
export const IconChat = (p: P) => (
  <Base {...p}>
    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
  </Base>
);
