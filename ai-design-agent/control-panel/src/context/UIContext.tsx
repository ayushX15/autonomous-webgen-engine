// 'use client'
// import { createContext, useContext, useState, ReactNode } from 'react'

// type UIMode = 'basic' | 'enhanced'
// interface UIContextType {
//   mode: UIMode
//   setMode: (m: UIMode) => void
//   isEnhanced: boolean
// }

// const UIContext = createContext<UIContextType>({
//   mode: 'basic', setMode: () => {}, isEnhanced: false
// })

// export function UIProvider({ children }: { children: ReactNode }) {
//   const [mode, setMode] = useState<UIMode>('basic')
//   return (
//     <UIContext.Provider value={{ mode, setMode, isEnhanced: mode === 'enhanced' }}>
//       {children}
//     </UIContext.Provider>
//   )
// }

// export function useUI() { return useContext(UIContext) }