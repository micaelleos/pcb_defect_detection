export interface DefectInfo {
  name: string;
  description: string;
  color: string;
}

/** As chaves são as classes retornadas pelo modelo. */
export const DEFECTS: Record<string, DefectInfo> = {
  missing_hole: {
    name: "Furo ausente",
    description: "Furo de fixação ou de passagem que não foi perfurado.",
    color: "#ff6b5e",
  },
  mouse_bite: {
    name: "Mordida de rato",
    description: "Erosão na borda da trilha que reduz a largura útil do condutor.",
    color: "#ffc247",
  },
  open_circuit: {
    name: "Circuito aberto",
    description: "Ruptura que interrompe a continuidade da trilha.",
    color: "#5cc8ff",
  },
  short: {
    name: "Curto-circuito",
    description: "Ligação de cobre indesejada entre trilhas vizinhas.",
    color: "#ff7ac6",
  },
  spur: {
    name: "Espora",
    description: "Pequena saliência de cobre projetada a partir da trilha.",
    color: "#b79cff",
  },
  spurious_copper: {
    name: "Cobre espúrio",
    description: "Resto de cobre isolado que permaneceu após a corrosão.",
    color: "#63e6a4",
  },
};

export function defectInfo(className: string): DefectInfo {
  return DEFECTS[className] ?? { name: className, description: "", color: "#ffffff" };
}
