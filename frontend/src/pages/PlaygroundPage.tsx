import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Check, ChevronDown, Copy, Plus, RotateCcw, Send, Square, Sparkles } from "lucide-react";
import { useAuth } from "../services/AuthContext";
import { getPlaygroundKey, listPlaygroundModels, streamCompletion, type PlaygroundModel } from "../services/playground";

type Message = { id: string; role: "user" | "assistant"; content: string };

export function PlaygroundPage() {
  const { user } = useAuth();
  const [models, setModels] = useState<PlaygroundModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [loadingModels, setLoadingModels] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const apiKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoadingModels(true);
    getPlaygroundKey(user.id).then((key) => {
      apiKeyRef.current = key;
      return listPlaygroundModels(key);
    }).then((data) => {
      if (!active) return;
      setModels(data);
      setSelectedModel((current) => current || data[0]?.id || "auto");
    }).catch((reason: Error) => active && setError(reason.message)).finally(() => active && setLoadingModels(false));
    return () => { active = false; abortRef.current?.abort(); };
  }, [user]);

  useEffect(() => { conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: "smooth" }); }, [messages, streaming]);
  const activeModel = useMemo(() => models.find((model) => model.id === selectedModel), [models, selectedModel]);
  const supportsSampling = activeModel?.owned_by === "groq" || activeModel?.owned_by === "openai";
  const newConversation = () => { abortRef.current?.abort(); setMessages([]); setDraft(""); setError(null); };

  const send = async () => {
    const content = draft.trim();
    if (!content || streaming || !apiKeyRef.current || !selectedModel) return;
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", content };
    const assistantId = crypto.randomUUID();
    const requestMessages = [...messages, userMessage].map(({ role, content: text }) => ({ role, content: text }));
    setMessages((current) => [...current, userMessage, { id: assistantId, role: "assistant", content: "" }]);
    setDraft(""); setError(null); setStreaming(true);
    const controller = new AbortController(); abortRef.current = controller;
    try {
      await streamCompletion(apiKeyRef.current, requestMessages, selectedModel, supportsSampling ? { temperature, maxTokens } : {}, controller.signal, (text) => {
        setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + text } : message));
      });
    } catch (reason) {
      if ((reason as Error).name !== "AbortError") setError((reason as Error).message);
    } finally { if (abortRef.current === controller) abortRef.current = null; setStreaming(false); }
  };

  return <div className="playground">
    <header className="playground__toolbar">
      <div className="playground__title"><div className="playground__title-icon"><Sparkles size={17} /></div><div><h1>RIM Playground</h1><p>Explore models through your gateway</p></div></div>
      <div className="playground__controls">
        <label className="playground__model-select"><span>Model</span><select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} disabled={loadingModels || streaming}>{loadingModels && <option>Loading models…</option>}{models.map((model) => <option key={`${model.owned_by}-${model.id}`} value={model.id}>{model.id}</option>)}</select><ChevronDown size={14} /></label>
        <div className="playground__provider"><Bot size={15} /><span>{activeModel ? activeModel.owned_by : "Gateway"}</span><small>{activeModel?.id || "Preparing models"}</small></div>
        {supportsSampling && <div style={{ display: "flex", alignItems: "center", gap: 8 }} aria-label="Generation settings">
          <label style={{ display: "grid", gridTemplateColumns: "auto 52px", alignItems: "center", gap: 6, color: "var(--color-text-subtle)", fontSize: 10 }}>Temperature <input style={samplingInputStyle} type="number" min="0" max="2" step="0.1" value={temperature} onChange={(event) => setTemperature(Math.min(2, Math.max(0, Number(event.target.value) || 0)))} disabled={streaming} /></label>
          <label style={{ display: "grid", gridTemplateColumns: "auto 52px", alignItems: "center", gap: 6, color: "var(--color-text-subtle)", fontSize: 10 }}>Max tokens <input style={samplingInputStyle} type="number" min="1" max="32768" step="1" value={maxTokens} onChange={(event) => setMaxTokens(Math.min(32768, Math.max(1, Number(event.target.value) || 1)))} disabled={streaming} /></label>
        </div>}
        <button className="playground__tool-button" type="button" onClick={() => setMessages([])} disabled={!messages.length || streaming}><RotateCcw size={15} />Clear</button>
        <button className="playground__new-button" type="button" onClick={newConversation}><Plus size={16} />New chat</button>
      </div>
    </header>
    <div className="playground__chat" ref={conversationRef}>
      <div className="playground__conversation">
        {!messages.length && !error && <Welcome model={activeModel} />}
        {messages.map((message) => <ChatMessage key={message.id} message={message} streaming={streaming && message.role === "assistant" && !message.content} />)}
        {error && <div className="playground__error"><strong>Request failed</strong><span>{error}</span></div>}
      </div>
    </div>
    <div className="playground__composer-wrap"><div className="playground__composer"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder={loadingModels ? "Preparing your Playground…" : "Message the model…"} disabled={loadingModels || streaming} rows={3} /><div className="playground__composer-bottom"><span>Enter to send <b>·</b> Shift + Enter for new line</span>{streaming ? <button className="playground__stop" type="button" onClick={() => abortRef.current?.abort()}><Square size={13} />Stop</button> : <button className="playground__send" type="button" onClick={() => void send()} disabled={!draft.trim() || loadingModels || !selectedModel}><Send size={16} />Send</button>}</div></div></div>
  </div>;
}

function Welcome({ model }: { model?: PlaygroundModel }) { return <section className="playground__welcome"><div className="playground__welcome-icon"><Sparkles size={22} /></div><h2>What can I help you build?</h2><p>{model ? `${model.id} is ready through ${model.owned_by}.` : "Your available gateway models will appear here."}</p><div className="playground__suggestions"><span>Explain a codebase</span><span>Draft an API design</span><span>Debug an error</span></div></section>; }

const samplingInputStyle = { width: 52, padding: "5px 4px", border: "1px solid var(--color-border)", borderRadius: 6, background: "var(--color-surface)", color: "var(--color-text)", fontSize: 11, textAlign: "center" as const, outline: "none" };

function ChatMessage({ message, streaming }: { message: Message; streaming: boolean }) { return <article className={`chat-message chat-message--${message.role}`}><div className="chat-message__avatar">{message.role === "user" ? "You" : <Bot size={16} />}</div><div className="chat-message__body"><div className="chat-message__label">{message.role === "user" ? "You" : "RIM"}</div>{message.content ? <Markdown content={message.content} /> : streaming && <div className="chat-message__typing"><i /><i /><i /></div>}{message.role === "assistant" && message.content && <CopyButton text={message.content} label="Copy response" />}</div></article>; }

function Markdown({ content }: { content: string }) { const parts = content.split(/```([\w+-]*)\n?([\s\S]*?)```/g); return <div className="markdown">{parts.map((part, index) => index % 3 === 2 ? <CodeBlock key={index} language={parts[index - 1] || "text"} code={part} /> : index % 3 === 0 && part ? <p key={index}>{inlineText(part)}</p> : null)}</div>; }
function inlineText(text: string) { return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((piece, index) => piece.startsWith("`") ? <code key={index}>{piece.slice(1, -1)}</code> : piece.startsWith("**") ? <strong key={index}>{piece.slice(2, -2)}</strong> : <span key={index}>{piece}</span>); }
function CodeBlock({ language, code }: { language: string; code: string }) { return <div className="code-block"><header><span>{language || "text"}</span><CopyButton text={code} label="Copy code" /></header><pre><code className={`language-${language}`}>{highlightCode(code)}</code></pre></div>; }
function highlightCode(code: string) { return code.split(/(\b(?:def|return|function|const|let|var|if|else|for|while|class|import|from|async|await|true|false|None|True|False)\b|(?:"[^"]*"|'[^']*')|\b\d+(?:\.\d+)?\b)/g).map((token, index) => /^(def|return|function|const|let|var|if|else|for|while|class|import|from|async|await|true|false|None|True|False)$/.test(token) ? <span className="syntax-keyword" key={index}>{token}</span> : /^("|')/.test(token) ? <span className="syntax-string" key={index}>{token}</span> : /^\d/.test(token) ? <span className="syntax-number" key={index}>{token}</span> : token); }
function CopyButton({ text, label }: { text: string; label: string }) { const [copied, setCopied] = useState(false); const copy = async () => { await navigator.clipboard?.writeText(text); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }; return <button className="copy-button" type="button" onClick={() => void copy()}>{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "Copied" : label}</button>; }
