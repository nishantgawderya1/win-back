import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { ProgressDots } from "../../components/common/index.jsx";

export default function Done() {
  const { session, finishOnboarding } = useAuth();
  const navigate = useNavigate();

  const open = () => {
    finishOnboarding();
    navigate(session?.mode === "batch" ? "/batch" : "/dashboard");
  };

  return (
    <>
      <ProgressDots total={3} current={3} />
      <p className="done-word mono accent">Ready.</p>

      <p className="ob-sub">
        WinBack is connected to your Razorpay account. The first payment failure will trigger the
        agent automatically.
      </p>
      <p className="ob-sub">
        {session?.mode === "batch"
          ? "Upload your first CSV to run a batch."
          : "Simulate a failure in Razorpay test-mode to watch the agent work."}
      </p>

      <button type="button" className="btn btn-primary btn-block" onClick={open}>
        Open dashboard →
      </button>
    </>
  );
}
