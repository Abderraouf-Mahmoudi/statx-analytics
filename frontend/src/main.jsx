import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";


function App() {
  return (
    <main className="grid min-h-screen place-items-center bg-statx-dark px-6 text-white">
      <section className="max-w-2xl text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.3em] text-statx-green">
          Football intelligence
        </p>
        <h1 className="text-5xl font-black sm:text-7xl">StatX Analytics</h1>
        <p className="mt-6 text-lg text-emerald-100">
          Assistant d’analyse tactique et de performance pour le football.
        </p>
      </section>
    </main>
  );
}


ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

