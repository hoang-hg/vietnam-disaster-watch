import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkUser = useCallback(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        if (parsed && typeof parsed === 'object' && (parsed.role || parsed.email)) {
          setUser(parsed);
        } else {
          setUser(null);
          localStorage.removeItem("user");
        }
      } catch (e) {
        setUser(null);
        localStorage.removeItem("user");
      }
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    checkUser();

    // Listen for storage events (cross-tab sync)
    const handleStorage = (e) => {
      if (e.key === "user" || e.type === "storage") {
        checkUser();
      }
    };

    // Custom event listener for api.js 401 triggers
    const handleAuthError = () => {
      setUser(null);
      localStorage.removeItem("user");
      localStorage.removeItem("access_token");
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener("auth:logout", handleAuthError);
    // We can also listen to specific 'auth:update' if needed

    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("auth:logout", handleAuthError);
    };
  }, [checkUser]);

  const login = (userData, token) => {
    localStorage.setItem("user", JSON.stringify(userData));
    localStorage.setItem("access_token", token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("access_token");
    setUser(null);
    // Dispatch storage event to sync other tabs
    window.dispatchEvent(new Event("storage"));
  };

  const updateUser = (data) => {
    const newUser = { ...user, ...data };
    setUser(newUser);
    localStorage.setItem("user", JSON.stringify(newUser));
    // Window dispatch might be needed if we want other tabs to update immediately, 
    // but the 'storage' event listener above handles it if setItem fires it (only other tabs)
  };

  return (
    <AuthContext.Provider value={{ user, loading, isAdmin: user?.role === 'admin', login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
