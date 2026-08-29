import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

class Boundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { err: null };
  }
  static getDerivedStateFromError(err) {
    return { err };
  }
  render() {
    if (this.state.err) {
      return (
        <pre style={{ color: "#ffd27a", padding: 24, whiteSpace: "pre-wrap" }}>
          UI error: {String(this.state.err?.message || this.state.err)}
          {"\n"}
          Hard-refresh after npm run build. If this persists, open an issue with this text.
        </pre>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <Boundary>
    <App />
  </Boundary>
);
