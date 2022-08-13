import { useState } from 'react';

export default function useUserData() {
  const getUserData = () => {
    const userData = sessionStorage.getItem('userdata');
    return userData;
  };

  const [userData, setUserData] = useState(getUserData());

  const saveUserData = (userData) => {
    sessionStorage.setItem('userdata', userData);
    setUserData(userData);
  };

  const removeUserData = () => {
    sessionStorage.removeItem('userdata');
    setUserData(null);
  };

  return {
    setUserData: saveUserData,
    userData,
    removeUserData
  };
}
