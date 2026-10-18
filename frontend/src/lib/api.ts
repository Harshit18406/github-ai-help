import axios from 'axios';

const baseURL=import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1';
export const api=axios.create({baseURL});

api.interceptors.request.use(config=>{
  const token=localStorage.getItem('access_token');
  if(token)config.headers.Authorization=`Bearer ${token}`;
  return config;
});

let refreshPromise:Promise<string>|null=null;

async function refreshAccessToken(){
  const refreshToken=localStorage.getItem('refresh_token');
  if(!refreshToken)throw new Error('No refresh token');

  if(!refreshPromise){
    refreshPromise=axios.post(`${baseURL}/auth/refresh`,{refresh_token:refreshToken})
      .then(({data})=>{
        localStorage.setItem('access_token',data.access_token);
        localStorage.setItem('refresh_token',data.refresh_token);
        return data.access_token as string;
      })
      .finally(()=>{refreshPromise=null});
  }

  return refreshPromise;
}

api.interceptors.response.use(
  response=>response,
  async error=>{
    const original=error.config as (typeof error.config & {_retry?:boolean})|undefined;
    if(error.response?.status!==401||!original||original._retry){
      return Promise.reject(error);
    }

    original._retry=true;
    try{
      const token=await refreshAccessToken();
      original.headers=original.headers||{};
      original.headers.Authorization=`Bearer ${token}`;
      return api(original);
    }catch(refreshError){
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_email');
      if(window.location.pathname!=='/login')window.location.href='/login';
      return Promise.reject(refreshError);
    }
  }
);
