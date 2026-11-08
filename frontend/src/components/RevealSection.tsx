import { useEffect, useRef, useState, type ReactNode } from "react";

/** Seção cujo conteúdo entra com animação ao aparecer na tela. */
export default function RevealSection({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(ref.current!);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} className={`section reveal${visible ? " is-visible" : ""}`}>
      {children}
    </section>
  );
}
