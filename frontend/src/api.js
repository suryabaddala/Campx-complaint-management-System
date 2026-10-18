import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:5001/api/v1",
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("campusfix_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function messageFromError(error) {
  return (
    error?.response?.data?.error?.message ||
    error?.message ||
    "Something went wrong. Please try again."
  );
}
