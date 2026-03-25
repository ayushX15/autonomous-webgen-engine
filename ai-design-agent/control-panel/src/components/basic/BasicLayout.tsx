// import InputPanel from '@/components/shared/InputPanel'
// import IterationViewer from '@/components/shared/IterationViewer'
// import OutputPanel from '@/components/shared/OutputPanel'
// import { RunRequest, RunStatus } from '@/lib/api'

// interface Props { status: RunStatus|null; isRunning: boolean; onSubmit: (r: RunRequest) => void }

// export default function BasicLayout({ status, isRunning, onSubmit }: Props) {
//   return (
//     <div className="min-h-screen bg-[#0a0f1e] p-5">
//       <div className="mb-5 pb-4 border-b border-[#1e293b]">
//         <h1 className="text-xl font-bold text-white">AI Design Agent</h1>
//         <p className="text-slate-500 text-sm mt-0.5">Agentic website generation · Basic Mode</p>
//       </div>
//       <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
//         <InputPanel onSubmit={onSubmit} isRunning={isRunning} />
//         <IterationViewer status={status} isRunning={isRunning} />
//         <OutputPanel status={status} />
//       </div>
//     </div>
//   )
// }