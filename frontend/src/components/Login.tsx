import { FirebaseError } from "firebase/app";
import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { useState, type CSSProperties } from "react";
import { DEFECTS } from "../defects";
import { auth } from "../firebase";
import inspectedBoard from "../img/placa-inspecionada.png";
import Brand from "./Brand";
import RevealSection from "./RevealSection";

const STEPS = [
  {
    title: "Fotografe a placa",
    text: "Use a câmera do celular ou envie uma imagem que você já tem.",
  },
  {
    title: "Aguarde a análise",
    text: "Um modelo de visão computacional treinado em defeitos de PCB examina a foto.",
  },
  {
    title: "Confira os pontos marcados",
    text: "Cada defeito aparece na imagem com o tipo e o nível de confiança.",
  },
];

/** Confiança de cada defeito marcado na imagem de exemplo, na ordem da numeração. */
const SAMPLE_CONFIDENCES = [93, 92, 92];

export default function Login() {
  const [error, setError] = useState<string | null>(null);

  async function login() {
    setError(null);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
    } catch (err) {
      if (err instanceof FirebaseError && err.code === "auth/popup-closed-by-user") return;
      setError("Não foi possível entrar. Tente novamente.");
    }
  }

  return (
    <div className="landing">
      <header className="topbar">
        <Brand />
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">Inspeção óptica de placas de circuito impresso</p>
            <h1>Veja os defeitos da sua PCB em uma foto.</h1>
            <p className="lead">
              Fotografe a placa e receba a imagem com cada falha de fabricação marcada e classificada.
              Sem equipamento dedicado, direto do navegador.
            </p>
            <button className="button button-primary" onClick={login}>
              Entrar com Google
            </button>
            {error && (
              <p className="alert" role="alert">
                {error}
              </p>
            )}
            <p className="fine-print">Suas fotos são usadas apenas na análise e não ficam armazenadas.</p>
          </div>
          <figure className="hero-demo">
            <div className="stage hero-stage">
              <img
                className="hero-image"
                src={inspectedBoard}
                width={701}
                height={364}
                alt="Placa de circuito impresso com três furos ausentes marcados e numerados pela análise"
              />
              <div className="scanline" />
            </div>
            <ol className="findings">
              {SAMPLE_CONFIDENCES.map((confidence, index) => (
                <li
                  key={index}
                  style={
                    {
                      "--i": index + 3,
                      "--confidence": confidence,
                      "--finding": DEFECTS.missing_hole.color,
                    } as CSSProperties
                  }
                >
                  <span className="finding-number" style={{ background: DEFECTS.missing_hole.color }}>
                    {index + 1}
                  </span>
                  <div className="finding-text">
                    <h3>{DEFECTS.missing_hole.name}</h3>
                    <p>{DEFECTS.missing_hole.description}</p>
                  </div>
                  <span className="confidence">{confidence}%</span>
                </li>
              ))}
            </ol>
          </figure>
        </section>

        <RevealSection>
          <h2>Como funciona</h2>
          <ol className="steps">
            {STEPS.map((step) => (
              <li key={step.title}>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </RevealSection>

        <RevealSection>
          <h2>Seis tipos de defeito, identificados pelo nome</h2>
          <ul className="defect-grid">
            {Object.entries(DEFECTS).map(([key, defect]) => (
              <li key={key}>
                <span className="swatch" style={{ background: defect.color }} />
                <div>
                  <h3>{defect.name}</h3>
                  <p>{defect.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </RevealSection>
      </main>

      <footer className="footer">
        Os resultados apoiam a inspeção e não substituem a verificação de um profissional qualificado.
      </footer>
    </div>
  );
}
