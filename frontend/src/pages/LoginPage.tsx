import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { Button } from "../components/Button";
import { useAdminKey } from "../services/adminKey";

export function LoginPage() {
  const { setAdminKey } = useAdminKey();
  const navigate = useNavigate();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Please paste your admin key to continue.");
      return;
    }
    setAdminKey(trimmed);
    navigate("/overview", { replace: true });
  };

  return (
    <div className="login">
      <div className="login__card">
        <div className="login__brand">
          <div className="login__logo">S</div>
          <div>
            <div className="login__brand-name">SmartLLM</div>
            <div className="login__brand-sub">Admin console</div>
          </div>
        </div>
        <h1 className="login__title">Sign in to continue</h1>
        <p className="login__description">
          Provide the admin key configured for the local SmartLLM gateway. The
          key is held only in this browser session and is never persisted to
          disk or transmitted outside the gateway.
        </p>
        <form onSubmit={handleSubmit} className="login__form">
          <label className="form-field">
            <span className="form-field__label">Admin key</span>
            <input
              className="form-field__input"
              type="password"
              autoComplete="current-password"
              autoFocus
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                setError(null);
              }}
              placeholder="sk-smartllm-admin-…"
            />
          </label>
          {error && <div className="login__error">{error}</div>}
          <Button variant="primary" type="submit">
            <ShieldCheck size={16} />
            Unlock dashboard
          </Button>
        </form>
        <div className="login__hint">
          Lost the key? Set <code>SMARTLLM_ADMIN_KEY</code> in the server
          environment and restart the gateway.
        </div>
      </div>
    </div>
  );
}
