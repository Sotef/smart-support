import { useEffect, useRef, useState } from "react";

const Chat = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { role: "system", text: "Введите текст обращения и нажмите отправить" },
  ]);
  const [analysis, setAnalysis] = useState(null);
  const [suggested, setSuggested] = useState([]);
  const [connecting, setConnecting] = useState(false);
  const [ragMode, setRagMode] = useState(false); // по умолчанию дословно из БЗ
  const wsRef = useRef(null);
  const clientIdRef = useRef(
    `client_${Math.random().toString(36).slice(2, 9)}`
  );

  useEffect(() => {
    // Инициализация WebSocket
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/${clientIdRef.current}`;

    try {
      setConnecting(true);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnecting(false);
        addSystemMsg("WebSocket подключён");
      };
      ws.onclose = () => {
        addSystemMsg("WebSocket отключён, используем HTTP");
      };
      ws.onerror = () => {
        addSystemMsg("Ошибка WebSocket, используем HTTP");
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "analysis_complete" || msg.type === "analysis_result") {
            handleAnalysisResult(msg.data);
          } else if (msg.type === "system_notification") {
            addSystemMsg(msg.message || "Системное уведомление");
          }
        } catch {}
      };
    } catch (e) {
      addSystemMsg("Не удалось подключиться к WebSocket");
    }

    return () => {
      try {
        wsRef.current?.close();
      } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addSystemMsg = (text) =>
    setMessages((prev) => [...prev, { role: "system", text }]);

  const addUserMsg = (text) =>
    setMessages((prev) => [...prev, { role: "user", text }]);

  const addBotMsg = (text) =>
    setMessages((prev) => [...prev, { role: "bot", text }]);

  const generateRequestId = () => `req_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    addUserMsg(text);
    setInput("");

    const payload = {
      request_id: generateRequestId(),
      text,
      channel: "web",
      metadata: { reply_mode: ragMode ? "gen" : "kb" }
    };

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({ type: "analyze_request", data: payload })
      );
      addSystemMsg("Отправлено через WebSocket, ожидаем анализ...");
      return;
    }

    // Fallback: HTTP
    try {
      addSystemMsg("Отправлено через HTTP, ожидаем анализ...");
      const resp = await fetch(`/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Ошибка анализа");
      const data = await resp.json();
      handleAnalysisResult(data);
    } catch (e) {
      addSystemMsg(`Ошибка: ${e.message || e}`);
    }
  };

  const handleAnalysisResult = (data) => {
    setAnalysis(data);
    setSuggested(data?.suggested_responses || []);

    // Отрисуем краткий итог в чат
    const cat = data?.classification;
    const conf = data?.confidence;
    addBotMsg(
      `Категория: ${cat} (${Math.round((conf || 0) * 100)}%). ` +
        (data?.recommendations?.insights?.[0] || "Рекомендации готовы.")
    );
  };

  const sendFeedback = async (quality = 5, responseUsed = true) => {
    if (!analysis?.request_id) return;
    try {
      await fetch(`/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: analysis.request_id,
          recommendation_quality: quality,
          response_used: responseUsed,
        }),
      });
      addSystemMsg("Спасибо за обратную связь!");
    } catch {}
  };

  return (
    <section className="chat">
      <div className="chat__header">
        <div>
          <h3>Smart Support</h3>
          {analysis ? (
            <div>
              <p>
                Категория (БЗ): <b>{analysis.kb_category || analysis.classification}</b>
                {analysis.kb_subcategory ? (
                  <>
                    {" "}| Подкатегория: <b>{analysis.kb_subcategory}</b>
                  </>
                ) : null}
                {" "}| Уверенность: <b>{Math.round((analysis.confidence || 0) * 100)}%</b>
              </p>
              {typeof analysis.sentiment_score === "number" ? (
                <p>
                  Тон: <b>{analysis.tone_label || "neutral"}</b>
                  {" "}({analysis.sentiment_score.toFixed(2)})
                </p>
              ) : null}
            </div>
          ) : (
            <p>{connecting ? "Подключение..." : "Готов к анализу"}</p>
          )}
        </div>
        <button className="close-btn" onClick={() => setAnalysis(null)}>Сбросить</button>
      </div>

      <div className="chat__body">
        <div style={{marginBottom:8}}>
          <label style={{display:"flex", alignItems:"center", gap:8}}>
            <input type="checkbox" checked={ragMode} onChange={(e)=>setRagMode(e.target.checked)} />
            Генеративный ответ (RAG) по БЗ
          </label>
        </div>
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={
              m.role === "user"
                ? "message message--client"
                : m.role === "bot"
                ? "message message--operator"
                : "message"
            }
          >
            <p>{m.text}</p>
          </div>
        ))}

        {analysis?.entities?.length ? (
          <div className="message">
            <p>
              <b>Сущности:</b>{" "}
              {analysis.entities
                .map((e) => `${e.type}: ${e.text}`)
                .join("; ")}
            </p>
          </div>
        ) : null}

        {analysis?.recommendations?.relevant_articles?.length ? (
          <div className="message">
            <p><b>Статьи БЗ (источники):</b></p>
            <ul>
              {analysis.recommendations.relevant_articles.slice(0,3).map((a,i)=>(
                <li key={i}>
                  <a href={`/api/knowledge-base/article/${a.id}`} target="_blank" rel="noreferrer">
                    <b>{a.title}</b>
                  </a>
                  <div style={{fontSize:"0.9em", opacity:0.9}}>
                    {(a.content || "").slice(0,200)}{(a.content||"").length>200?"...":""}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {analysis?.recommendations?.actions?.length ? (
          <div className="message">
            <p>
              <b>Действия:</b>
            </p>
            <ul>
              {analysis.recommendations.actions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {suggested.length ? (
          <div className="message">
            <p><b>Предлагаемые ответы:</b></p>
            <ul>
              {suggested.map((s, i) => (
                <li key={i}>
                  <button
                    className="send-btn"
                    onClick={() => navigator.clipboard.writeText(s)}
                    title="Скопировать"
                  >
                    📋
                  </button>{" "}
                  {s}
                </li>
              ))}
            </ul>
            <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
              <button className="close-btn" onClick={() => sendFeedback(5, true)}>
                ✅ Решено
              </button>
              <button className="close-btn" onClick={() => sendFeedback(1, false)}>
                ❌ Не решено
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="chat__input">
        <input
          type="text"
          placeholder="Опишите обращение клиента..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button className="send-btn" onClick={handleSend}>➤</button>
      </div>
    </section>
  );
};

export default Chat;
