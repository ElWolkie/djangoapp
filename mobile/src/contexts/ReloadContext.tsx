// src/contexts/ReloadContext.tsx
import React, { createContext, useState } from 'react';

export const ReloadContext = createContext({
  reloadCount: 0,
  triggerReload: () => {},
});

export const ReloadProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [reloadCount, setReloadCount] = useState(0);
  const triggerReload = () => setReloadCount(c => c + 1);
  return (
    <ReloadContext.Provider value={{ reloadCount, triggerReload }}>
      {children}
    </ReloadContext.Provider>
  );
};
