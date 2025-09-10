import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Grader from '../Grader.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Grader/>
  </StrictMode>,
)
