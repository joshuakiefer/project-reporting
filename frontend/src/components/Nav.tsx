interface NavProps {
  current: string;
  onNavigate: (page: "overlay" | "dashboard" | "settings") => void;
}

export default function Nav({ current, onNavigate }: NavProps) {
  const items = [
    { id: "overlay" as const, label: "Assistant" },
    { id: "dashboard" as const, label: "Insights" },
    { id: "settings" as const, label: "Settings" },
  ];

  return (
    <nav className="nav">
      <div className="nav-brand">WorkOptimize</div>
      <div className="nav-items">
        {items.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${current === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
