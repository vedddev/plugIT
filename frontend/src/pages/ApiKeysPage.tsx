import { useMemo, useState } from "react";
import { Plus, Copy, RefreshCcw, X, ShieldOff } from "lucide-react";
import { TopBar } from "../layouts/TopBar";
import { Button } from "../components/Button";
import { DataTable, type Column } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { Modal } from "../components/Modal";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import { formatRelative, formatTimestamp } from "../services/format";
import type { ApiKey, ApiKeyCreated } from "../types/api";

export function ApiKeysPage() {
  const toast = useToast();
  const asyncState = useAsync(() => api.listApiKeys(), []);
  const [createOpen, setCreateOpen] = useState(false);
  const [rotated, setRotated] = useState<ApiKeyCreated | null>(null);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [pendingRevoke, setPendingRevoke] = useState<ApiKey | null>(null);

  const refresh = () => asyncState.reload();

  const handleError = (err: Error) => {
    if (err instanceof ApiError && err.isAuth) return;
    toast.show("error", "API key operation failed", err.message);
  };

  if (asyncState.error) handleError(asyncState.error);

  const data = asyncState.data?.data ?? [];

  const columns: Column<ApiKey>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Name",
        cell: (row) => (
          <div>
            <div className="strong">{row.name}</div>
            <div className="muted mono small">{row.key_prefix}…</div>
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        width: "120px",
        cell: (row) =>
          row.is_active ? (
            <span className="pill pill--success">Active</span>
          ) : (
            <span className="pill pill--muted">Revoked</span>
          ),
      },
      {
        key: "created",
        header: "Created",
        width: "180px",
        cell: (row) => formatTimestamp(row.created_at),
      },
      {
        key: "last_used",
        header: "Last used",
        width: "140px",
        cell: (row) => formatRelative(row.last_used_at),
      },
      {
        key: "expires",
        header: "Expires",
        width: "160px",
        cell: (row) => (row.expires_at ? formatTimestamp(row.expires_at) : "Never"),
      },
      {
        key: "actions",
        header: "",
        align: "right",
        cell: (row) => (
          <div className="row-actions">
            <Button
              size="sm"
              variant="secondary"
              disabled={!row.is_active}
              onClick={(e) => {
                e.stopPropagation();
                api
                  .rotateApiKey(row.id)
                  .then((result) => {
                    setRotated(result);
                    refresh();
                    toast.show("success", "API key rotated", "Copy the new secret below — it will not be shown again.");
                  })
                  .catch((err) => {
                    toast.show("error", "Could not rotate key", err.message);
                  });
              }}
              title="Rotate this key"
            >
              <RefreshCcw size={14} />
              Rotate
            </Button>
            <Button
              size="sm"
              variant="danger"
              disabled={!row.is_active}
              onClick={(e) => {
                e.stopPropagation();
                setPendingRevoke(row);
              }}
            >
              <ShieldOff size={14} />
              Revoke
            </Button>
          </div>
        ),
      },
    ],
    [refresh, toast],
  );

  return (
    <>
      <TopBar
        title="API keys"
        description="Manage tokens used to authenticate against the SmartLLM gateway."
        onRefresh={refresh}
        loading={asyncState.loading}
      />
      <div className="page">
        <section className="card card--padded">
          <header className="card__header card__header--with-action">
            <div>
              <h2>Active tokens</h2>
              <p className="muted small">
                Secrets are never stored on the server. Newly generated keys are
                shown only once after creation or rotation.
              </p>
            </div>
            <Button
              variant="primary"
              size="md"
              onClick={() => setCreateOpen(true)}
            >
              <Plus size={14} />
              Create key
            </Button>
          </header>
          <DataTable
            columns={columns}
            data={data}
            rowKey={(row) => row.id}
            isLoading={asyncState.loading}
            emptyState={
              <EmptyState
                title="No API keys yet"
                description="Create a key to let clients authenticate against the gateway."
                action={
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => setCreateOpen(true)}
                  >
                    <Plus size={14} />
                    Create first key
                  </Button>
                }
              />
            }
          />
        </section>
      </div>

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Create API key"
        size="sm"
      >
        <CreateKeyForm
          onCancel={() => setCreateOpen(false)}
          onCreated={(key) => {
            setCreated(key);
            setCreateOpen(false);
            refresh();
          }}
        />
      </Modal>

      <Modal
        open={Boolean(created)}
        onClose={() => setCreated(null)}
        title="API key created"
        size="sm"
        footer={
          <div className="modal__footer-actions">
            <Button variant="secondary" onClick={() => setCreated(null)}>
              <X size={14} />
              I have saved the key
            </Button>
          </div>
        }
      >
        {created && <SecretDisplay name={created.name} secret={created.key} warning="Copy this secret now. It cannot be retrieved again." />}
      </Modal>

      <Modal
        open={Boolean(rotated)}
        onClose={() => setRotated(null)}
        title="API key rotated"
        size="sm"
        footer={
          <div className="modal__footer-actions">
            <Button variant="secondary" onClick={() => setRotated(null)}>
              <X size={14} />
              I have saved the key
            </Button>
          </div>
        }
      >
        {rotated && <SecretDisplay name={rotated.name} secret={rotated.key} warning="The previous secret is now invalid. Copy the new secret now." />}
      </Modal>

      <Modal
        open={Boolean(pendingRevoke)}
        onClose={() => setPendingRevoke(null)}
        title="Revoke API key"
        size="sm"
        footer={
          <div className="modal__footer-actions">
            <Button variant="ghost" onClick={() => setPendingRevoke(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (!pendingRevoke) return;
                api
                  .revokeApiKey(pendingRevoke.id)
                  .then(() => {
                    toast.show("success", "Key revoked", "Clients using this secret will no longer be able to authenticate.");
                    setPendingRevoke(null);
                    refresh();
                  })
                  .catch((err) => {
                    toast.show("error", "Could not revoke key", err.message);
                  });
              }}
            >
              <ShieldOff size={14} />
              Revoke key
            </Button>
          </div>
        }
      >
        {pendingRevoke && (
          <p>
            Are you sure you want to revoke <strong>{pendingRevoke.name}</strong>?
            Any client using this key will need to be updated with a new key.
          </p>
        )}
      </Modal>
    </>
  );
}

function CreateKeyForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (key: ApiKeyCreated) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [expiration, setExpiration] = useState("");
  const [metadata, setMetadata] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Please provide a name for this key.");
      return;
    }
    setSubmitting(true);
    setError(null);
    api
      .createApiKey({
        name: name.trim(),
        expires_at: expiration ? new Date(expiration).toISOString() : null,
        metadata: metadata.trim() || null,
      })
      .then((result) => {
        onCreated(result);
        toast.show("success", "API key created", "Copy the new secret before closing the dialog.");
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <form onSubmit={submit} className="form">
      <label className="form-field">
        <span className="form-field__label">Name</span>
        <input
          className="form-field__input"
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Production integration"
          required
        />
      </label>
      <label className="form-field">
        <span className="form-field__label">Expiration (optional)</span>
        <input
          className="form-field__input"
          type="datetime-local"
          value={expiration}
          onChange={(e) => setExpiration(e.target.value)}
        />
      </label>
      <label className="form-field">
        <span className="form-field__label">Metadata (optional)</span>
        <input
          className="form-field__input"
          value={metadata}
          onChange={(e) => setMetadata(e.target.value)}
          placeholder="Owner, environment, notes…"
        />
      </label>
      {error && <div className="form__error">{error}</div>}
      <div className="form__actions">
        <Button variant="ghost" type="button" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="primary" type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create key"}
        </Button>
      </div>
    </form>
  );
}

function SecretDisplay({ name, secret, warning }: { name: string; secret: string; warning: string }) {
  const toast = useToast();
  return (
    <div>
      <div className="alert alert--warning">{warning}</div>
      <div className="form-field">
        <span className="form-field__label">Secret for {name}</span>
        <div className="secret-display">
          <code className="mono secret-display__value">{secret}</code>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (navigator.clipboard?.writeText) {
                navigator.clipboard
                  .writeText(secret)
                  .then(() => toast.show("success", "Copied", "Secret copied to clipboard."))
                  .catch(() => toast.show("error", "Copy failed", "Copy the secret manually from the field above."));
              } else {
                toast.show("error", "Copy unsupported", "Copy the secret manually from the field above.");
              }
            }}
          >
            <Copy size={14} />
            Copy
          </Button>
        </div>
      </div>
    </div>
  );
}
