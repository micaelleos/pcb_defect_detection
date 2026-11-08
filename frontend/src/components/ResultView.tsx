import { useState, type CSSProperties } from "react";
import type { PredictResponse } from "../api";
import { defectInfo } from "../defects";

interface Props {
  imageUrl: string;
  result: PredictResponse;
  onReset: () => void;
}

export default function ResultView({ imageUrl, result, onReset }: Props) {
  const { width, height, detections } = result;
  const [active, setActive] = useState<number | null>(null);
  const count = detections.length;

  return (
    <section className="result">
      <header className="result-header">
        <div>
          <p className="eyebrow">Resultado da inspeção</p>
          <h1>
            {count === 0
              ? "Nenhum defeito detectado"
              : count === 1
                ? "1 defeito encontrado"
                : `${count} defeitos encontrados`}
          </h1>
        </div>
        <button className="button button-secondary" onClick={onReset}>
          Analisar outra placa
        </button>
      </header>

      <div className="result-body">
        <div className="stage">
          <img src={imageUrl} alt="Placa analisada" />
          {detections.map(({ box, class_name }, index) => (
            <div
              key={index}
              className={`marker${active === index ? " marker-active" : ""}`}
              style={
                {
                  left: `${(box.x_min / width) * 100}%`,
                  top: `${(box.y_min / height) * 100}%`,
                  width: `${((box.x_max - box.x_min) / width) * 100}%`,
                  height: `${((box.y_max - box.y_min) / height) * 100}%`,
                  "--marker": defectInfo(class_name).color,
                  "--i": index,
                } as CSSProperties
              }
            >
              <span className="marker-tag">{index + 1}</span>
            </div>
          ))}
        </div>

        {count === 0 ? (
          <p className="empty">
            O modelo não identificou falhas nesta foto. Defeitos muito pequenos podem passar despercebidos: em caso de
            dúvida, repita a foto mais perto da área suspeita.
          </p>
        ) : (
          <ol className="findings">
            {detections.map((detection, index) => {
              const defect = defectInfo(detection.class_name);
              return (
                <li
                  key={index}
                  style={
                    {
                      "--i": index,
                      "--confidence": Math.round(detection.confidence * 100),
                      "--finding": defect.color,
                    } as CSSProperties
                  }
                  onMouseEnter={() => setActive(index)}
                  onMouseLeave={() => setActive(null)}
                >
                  <span className="finding-number" style={{ background: defect.color }}>
                    {index + 1}
                  </span>
                  <div className="finding-text">
                    <h2>{defect.name}</h2>
                    <p>{defect.description}</p>
                  </div>
                  <span className="confidence" title="Confiança do modelo nesta detecção">
                    {Math.round(detection.confidence * 100)}%
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
