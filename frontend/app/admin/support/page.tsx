"use client";

import { getWsBase } from "@/lib/ws";
import { useEffect, useRef, useState } from "react";
import {
  Send,
  Users,
  MessageSquare,
  Wifi,
  WifiOff,
  Loader2,
  RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import { useStore } from "@/store/useStore";

interface UserChat {
  user_id: string;
  messages: { from: "user" | "admin"; message: string; time: string }[];
  unread: number;
  isOnline: boolean;
}

export default function AdminSupportPage() {
  const { user } = useStore();
  const [activeUsers, setActiveUsers] = useState<UserChat[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeUsers, selectedUser]);

  // Connect WebSocket
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const connect = async () => {
      const wsBase = await getWsBase();
      if (!isMounted) return;
      const ws = new WebSocket(`${wsBase}/support/ws/chat/admin/${user.id}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setIsConnected(true);
        setIsReconnecting(false);
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);

          // New user online
          if (data.type === "user_online") {
            setActiveUsers((prev) => {
              if (prev.find((u) => u.user_id === data.user_id)) return prev;
              return [
                ...prev,
                {
                  user_id: data.user_id,
                  messages: [],
                  unread: 0,
                  isOnline: true,
                },
              ];
            });
            toast.success(`New user connected: ${data.user_id.substring(0, 8)}`);
          }

          // User offline
          if (data.type === "user_offline") {
            setActiveUsers((prev) =>
              prev.map((u) =>
                u.user_id === data.user_id ? { ...u, isOnline: false } : u
              )
            );
          }

          // New chat message
          if (data.type === "chat_message" && data.from === "user") {
            setActiveUsers((prev) => {
              const existing = prev.find((u) => u.user_id === data.user_id);
              const newMessage = {
                from: "user" as const,
                message: data.message,
                time: new Date().toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
              };

              if (existing) {
                return prev.map((u) =>
                  u.user_id === data.user_id
                    ? {
                        ...u,
                        messages: [...u.messages, newMessage],
                        unread:
                          selectedUser === data.user_id ? 0 : u.unread + 1,
                      }
                    : u
                );
              }

              // First message from this user
              return [
                ...prev,
                {
                  user_id: data.user_id,
                  messages: [newMessage],
                  unread: selectedUser === data.user_id ? 0 : 1,
                  isOnline: true,
                },
              ];
            });
          }
        } catch (e) {
          console.error("Parse error:", e);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setIsConnected(false);
        setIsReconnecting(true);
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMounted) connect();
        }, 3000);
      };

      ws.onerror = () => {
        if (!isMounted) return;
        setIsConnected(false);
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [user, selectedUser]);

  // Send reply
  const sendMessage = () => {
    if (!input.trim() || !selectedUser || !isConnected) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          target_user_id: selectedUser,
          message: input,
        })
      );

      // Add to local state
      setActiveUsers((prev) =>
        prev.map((u) =>
          u.user_id === selectedUser
            ? {
                ...u,
                messages: [
                  ...u.messages,
                  {
                    from: "admin" as const,
                    message: input,
                    time: new Date().toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
                  },
                ],
              }
            : u
        )
      );
      setInput("");
    }
  };

  const selectUser = (userId: string) => {
    setSelectedUser(userId);
    // Mark as read
    setActiveUsers((prev) =>
      prev.map((u) => (u.user_id === userId ? { ...u, unread: 0 } : u))
    );
  };

  const currentChat = activeUsers.find((u) => u.user_id === selectedUser);

  return (
    <div className="max-w-7xl mx-auto">
      {/* ==========================================
          HEADER
      ========================================== */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="text-primary" size={28} />
            <h1 className="text-2xl md:text-3xl font-bold">Support Console</h1>
          </div>
          <p className="text-text-muted text-sm">
            Reply to user messages in real-time
          </p>
        </div>
        <div
          className={`text-xs px-3 py-1.5 rounded-full flex items-center gap-1.5 self-start ${
            isConnected
              ? "bg-success/20 text-success"
              : isReconnecting
              ? "bg-warning/20 text-warning"
              : "bg-danger/20 text-danger"
          }`}
        >
          {isConnected ? (
            <>
              <Wifi size={12} /> Connected
            </>
          ) : isReconnecting ? (
            <>
              <Loader2 size={12} className="animate-spin" /> Reconnecting...
            </>
          ) : (
            <>
              <WifiOff size={12} /> Offline
            </>
          )}
        </div>
      </div>

      {/* ==========================================
          MAIN LAYOUT
      ========================================== */}
      <div className="h-[calc(100vh-220px)] min-h-[500px] flex flex-col md:flex-row gap-4">
        {/* ==========================================
            USERS LIST (Sidebar)
        ========================================== */}
        <div className="w-full md:w-72 bg-surface border border-gray-700 rounded-xl flex flex-col flex-shrink-0">
          <div className="p-3 border-b border-gray-700">
            <h2 className="font-bold flex items-center gap-2 text-sm">
              <Users size={16} /> Active Users ({activeUsers.length})
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {activeUsers.length === 0 ? (
              <div className="p-6 text-center">
                <p className="text-sm text-text-muted">No active users</p>
                <p className="text-xs text-text-muted mt-1">
                  Users will appear here when they start a chat
                </p>
              </div>
            ) : (
              activeUsers.map((u) => {
                const lastMessage = u.messages[u.messages.length - 1];
                return (
                  <button
                    key={u.user_id}
                    onClick={() => selectUser(u.user_id)}
                    className={`w-full text-left p-3 border-b border-gray-800 hover:bg-background transition flex items-center gap-2 ${
                      selectedUser === u.user_id
                        ? "bg-primary/10 border-l-2 border-l-primary"
                        : ""
                    }`}
                  >
                    <div className="relative flex-shrink-0">
                      <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
                        U
                      </div>
                      {u.isOnline && (
                        <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-success rounded-full border-2 border-surface"></span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        User {u.user_id.substring(0, 8)}
                      </p>
                      <p className="text-xs text-text-muted truncate">
                        {lastMessage?.message || "No messages"}
                      </p>
                    </div>
                    {u.unread > 0 && (
                      <span className="bg-danger text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0">
                        {u.unread > 9 ? "9+" : u.unread}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ==========================================
            CHAT AREA
        ========================================== */}
        <div className="flex-1 bg-surface border border-gray-700 rounded-xl flex flex-col min-h-[400px]">
          {!selectedUser ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare
                  size={48}
                  className="text-text-muted/30 mx-auto mb-3"
                />
                <p className="text-text-muted">
                  Select a user to start chatting
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="p-3 border-b border-gray-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
                    U
                  </div>
                  <div>
                    <p className="font-bold text-sm">
                      User {selectedUser.substring(0, 8)}
                    </p>
                    <p
                      className={`text-xs flex items-center gap-1 ${
                        currentChat?.isOnline
                          ? "text-success"
                          : "text-text-muted"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          currentChat?.isOnline
                            ? "bg-success animate-pulse"
                            : "bg-gray-500"
                        }`}
                      ></span>
                      {currentChat?.isOnline ? "Online" : "Offline"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-background/30">
                {currentChat?.messages.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-sm text-text-muted">
                      No messages yet from this user.
                    </p>
                  </div>
                ) : (
                  currentChat?.messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${
                        msg.from === "admin" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
                          msg.from === "admin"
                            ? "bg-primary text-white rounded-br-sm"
                            : "bg-surface border border-gray-700 rounded-bl-sm"
                        }`}
                      >
                        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                          {msg.message}
                        </p>
                        <p
                          className={`text-[10px] mt-1 ${
                            msg.from === "admin"
                              ? "text-white/70 text-right"
                              : "text-text-muted"
                          }`}
                        >
                          {msg.time}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-3 border-t border-gray-700 flex gap-2 bg-background/50">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  placeholder={
                    isConnected ? "Type your reply..." : "Reconnecting..."
                  }
                  disabled={!isConnected}
                  className="flex-1 px-4 py-3 bg-background border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary outline-none disabled:opacity-50 text-sm"
                />
                <button
                  onClick={sendMessage}
                  disabled={!isConnected || !input.trim()}
                  className="px-4 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send size={18} />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}