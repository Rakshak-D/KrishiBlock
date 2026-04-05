import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error) {
    this.setState({ error });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="detail-card error-panel" role="alert">
          <p className="eyebrow">Something went wrong</p>
          <h2>We hit an unexpected UI error.</h2>
          <p>{this.state.error?.message || "Please reload the page and try again."}</p>
          <button className="primary-button" onClick={this.handleReset} type="button">Try again</button>
        </div>
      );
    }

    return this.props.children;
  }
}
