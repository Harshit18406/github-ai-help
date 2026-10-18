import type {ReactNode} from 'react';
import {Navigate, Route, Routes} from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import RepositoryWorkspace from './pages/RepositoryWorkspace';

function Protected({children}:{children:ReactNode}) {
  return localStorage.getItem('access_token') ? <>{children}</> : <Navigate to="/login" replace/>;
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<Login/>}/>
    <Route path="/register" element={<Register/>}/>
    <Route path="/" element={<Protected><Dashboard/></Protected>}/>
    <Route path="/repositories/:id" element={<Protected><RepositoryWorkspace/></Protected>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes>;
}
