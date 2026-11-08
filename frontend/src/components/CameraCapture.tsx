import type { ChangeEvent } from "react";

interface Props {
  onSelect: (file: File) => void;
}

const TIPS = [
  "Fotografe de cima, com a câmera paralela à placa.",
  "Use luz uniforme e evite reflexos no cobre.",
  "Enquadre a placa inteira, ocupando a maior parte da foto.",
];

export default function CameraCapture({ onSelect }: Props) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Limpa o valor para permitir escolher a mesma foto novamente.
    event.target.value = "";
    if (file) onSelect(file);
  }

  return (
    <section className="capture">
      <div className="capture-main">
        <h1>Nova inspeção</h1>
        <p className="lead">Tire uma foto da placa ou envie uma imagem para começar.</p>
        <div className="actions">
          <label className="button button-primary">
            Fotografar placa
            <input type="file" accept="image/*" capture="environment" className="visually-hidden" onChange={handleChange} />
          </label>
          <label className="button button-secondary">
            Enviar imagem
            <input type="file" accept="image/*" className="visually-hidden" onChange={handleChange} />
          </label>
        </div>
      </div>
      <aside className="tips">
        <h2>Para um resultado melhor</h2>
        <ul>
          {TIPS.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </aside>
    </section>
  );
}
