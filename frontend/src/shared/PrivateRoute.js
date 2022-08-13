import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { apiUrl } from './Variables';

import SessionExpiredPage from '../components/Session-expired.component';
import useToken from '../hooks/useToken';

export const PrivateRoute = ({ children }) => {
  let navigate = useNavigate();
  const { token } = useToken();
  const [auth, setAuth] = useState(false);
  const [isTokenValidated, setIsTokenValidated] = useState(false);

  useEffect(() => {
    // Send jwt to API to see if it's valid
    if (token) {
      var url = apiUrl + '/user/validate';
      axios({
        method: 'POST',
        responseType: 'json',
        url: url,
        headers: {
          Authorization: 'Bearer ' + token
        }
      })
        .then(function () {
          setAuth(true);
          setIsTokenValidated(true);
        })
        .catch(function (error) {
          console.log(error);
          setAuth(false);
          setIsTokenValidated(false);
          sessionStorage.removeItem('token');
        });
    } else {
      setIsTokenValidated(true); // in case there is no token
    }
  }, []);

  if (!isTokenValidated) return <SessionExpiredPage />; // or some kind of loading animation

  return auth ? children : navigate('/login');
};
