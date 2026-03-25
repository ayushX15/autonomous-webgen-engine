// 'use client'
// import { useUI } from '@/context/UIContext'

// export default function UIToggle() {
//   const { isEnhanced, setMode } = useUI()
//   return (
//     <div className="flex items-center gap-3">
//       <span className={`text-xs font-semibold uppercase tracking-widest transition-colors ${!isEnhanced ? 'text-white' : 'text-slate-500'}`}>
//         Basic
//       </span>
//       <button
//         onClick={() => setMode(isEnhanced ? 'basic' : 'enhanced')}
//         className={`relative w-12 h-6 rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${
//           isEnhanced ? 'bg-gradient-to-r from-indigo-600 to-purple-600 glow-pulse' : 'bg-slate-700'
//         }`}
//       >
//         <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-lg transition-all duration-300 ${
//           isEnhanced ? 'left-6' : 'left-0.5'
//         }`} />
//       </button>
//       <span className={`text-xs font-semibold uppercase tracking-widest transition-colors ${isEnhanced ? 'text-indigo-400' : 'text-slate-500'}`}>
//         Enhanced
//       </span>
//     </div>
//   )
// }