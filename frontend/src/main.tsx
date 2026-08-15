import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import { AdminKeyProvider } from "./services/adminKey";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("app")!).render(
  <React.StrictMode>
    <HashRouter>
      <AdminKeyProvider>
        <App />
      </AdminKeyProvider>
    </HashRouter>
  </React.StrictMode>,
);
