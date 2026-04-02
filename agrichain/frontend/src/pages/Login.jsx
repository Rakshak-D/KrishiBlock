import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import AccessIntro from "../components/auth/AccessIntro";
import AccessPanel from "../components/auth/AccessPanel";
import { agrichainApi } from "../services/api";
import useAuthStore from "../store/authStore";

function validatePhone(value) {
  const normalized = value.trim();
  if (!normalized) return "Phone number is required.";
  return /^\+?[0-9]{10,15}$/.test(normalized) ? "" : "Enter a valid phone number.";
}

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [mode, setMode] = useState("register");
  const [submitting, setSubmitting] = useState(false);
  const [otpRequested, setOtpRequested] = useState(false);
  const [otp, setOtp] = useState("");
  const [phone, setPhone] = useState("");
  const [registerForm, setRegisterForm] = useState({ name: "", village: "", user_type: "farmer", language: "en", market_type: "local" });
  const overviewQuery = useQuery({ queryKey: ["login-overview"], queryFn: agrichainApi.listingsOverview });

  const phoneError = useMemo(() => validatePhone(phone), [phone]);
  const otpError = useMemo(() => (!otpRequested || /^\d{6}$/.test(otp) ? "" : "Enter the 6-digit OTP."), [otp, otpRequested]);
  const stats = useMemo(() => ({
    totalListings: overviewQuery.data?.total_listings || 0,
    activeFarmers: overviewQuery.data?.active_farmers || 0,
    localAverage: new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(overviewQuery.data?.by_market?.local?.avg_price || 0),
    globalAverage: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(overviewQuery.data?.by_market?.global?.avg_price || 0),
  }), [overviewQuery.data]);

  useEffect(() => {
    setOtpRequested(false);
    setOtp("");
  }, [mode, phone]);

  const submitRegister = async () => {
    if (phoneError) return toast.error(phoneError);
    if (registerForm.name.trim().length < 3) return toast.error("Enter a valid full name.");
    setSubmitting(true);
    try {
      const result = await agrichainApi.register({ phone, ...registerForm });
      login(result.token, result.user);
      toast.success(result.onboarding?.message || "Account created.");
      navigate("/dashboard");
    } finally {
      setSubmitting(false);
    }
  };

  const requestOtp = async () => {
    if (phoneError) return toast.error(phoneError);
    setSubmitting(true);
    try {
      const result = await agrichainApi.requestOtp({ phone });
      if (result.dev_otp) {
        setOtp(result.dev_otp);
      }
      setOtpRequested(true);
      toast.success(result.message || "OTP sent.");
    } finally {
      setSubmitting(false);
    }
  };

  const verifyOtp = async () => {
    if (phoneError || otpError) return toast.error(phoneError || otpError);
    setSubmitting(true);
    try {
      const result = await agrichainApi.verifyOtp({ phone, otp });
      login(result.token, result.user);
      toast.success("Signed in successfully.");
      navigate("/dashboard");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-shell auth-layout auth-layout-expanded">
      <AccessIntro stats={stats} />
      <AccessPanel
        mode={mode}
        setMode={setMode}
        phone={phone}
        setPhone={setPhone}
        phoneError={phoneError}
        registerForm={registerForm}
        onRegisterField={(field, value) => setRegisterForm((current) => ({ ...current, [field]: value }))}
        submitting={submitting}
        submitRegister={submitRegister}
        otpRequested={otpRequested}
        requestOtp={requestOtp}
        otp={otp}
        setOtp={setOtp}
        otpError={otpError}
        verifyOtp={verifyOtp}
      />
    </section>
  );
}
