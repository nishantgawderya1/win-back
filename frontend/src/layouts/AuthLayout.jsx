import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="centered-page">
      <Outlet />
    </div>
  );
}
