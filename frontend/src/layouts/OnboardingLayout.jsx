import { Outlet } from "react-router-dom";

export default function OnboardingLayout() {
  return (
    <div className="centered-page">
      <div className="onboarding">
        <Outlet />
      </div>
    </div>
  );
}
