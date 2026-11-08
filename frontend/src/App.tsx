import { onAuthStateChanged, signOut, type User } from "firebase/auth";
import { useEffect, useState } from "react";
import { predict, resizeImage, type PredictResponse } from "./api";
import Brand from "./components/Brand";
import CameraCapture from "./components/CameraCapture";
import Login from "./components/Login";
import ResultView from "./components/ResultView";
import { auth } from "./firebase";

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  useEffect(() => {
    if (!imageUrl) return;
    return () => URL.revokeObjectURL(imageUrl);
  }, [imageUrl]);

  function reset() {
    setImageUrl(null);
    setResult(null);
  }

  async function analyze(file: File) {
    if (!user) return;
    setError(null);
    reset();

    let image: Blob;
    try {
      image = await resizeImage(file);
    } catch {
      setError("Não conseguimos abrir esta imagem. Envie uma foto em JPG ou PNG.");
      return;
    }

    setImageUrl(URL.createObjectURL(image));
    try {
      setResult(await predict(image, user));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível analisar a imagem. Tente novamente.");
      reset();
    }
  }

  if (user === undefined) return <div className="splash" aria-label="Carregando" />;
  if (user === null) return <Login />;

  return (
    <div className="app">
      <header className="topbar">
        <Brand />
        <div className="account">
          <span className="account-name">{user.email}</span>
          <button className="text-button" onClick={() => signOut(auth)}>
            Sair
          </button>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
        {!imageUrl && <CameraCapture onSelect={analyze} />}
        {imageUrl && !result && (
          <section className="analyzing">
            <p className="eyebrow" role="status">
              Analisando a placa…
            </p>
            <div className="stage">
              <img src={imageUrl} alt="Placa em análise" />
              <div className="scanline" />
            </div>
          </section>
        )}
        {imageUrl && result && <ResultView imageUrl={imageUrl} result={result} onReset={reset} />}
      </main>

      <footer className="footer">
        Os resultados apoiam a inspeção e não substituem a verificação de um profissional qualificado.
      </footer>
    </div>
  );
}
