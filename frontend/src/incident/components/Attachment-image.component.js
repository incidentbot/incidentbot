import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Skeleton from '@mui/material/Skeleton';

export default function AttachmentImage({ item, token }) {
  const [attachmentImage, setAttachmentImage] = useState(null);
  const Buffer = require('buffer/').Buffer;
  const [loading, setLoading] = useState(false);

  async function getImageBinaryToBase64() {
    await axios({
      method: 'GET',
      responseType: 'arraybuffer',
      url: item.img,
      headers: {
        Authorization: 'Bearer ' + token
      }
    }).then(function (response) {
      setAttachmentImage(Buffer.from(response.data, 'binary').toString('base64'));
    });
  }

  useEffect(() => {
    getImageBinaryToBase64();
    setLoading(false);
  }, []);

  return loading ? (
    <Skeleton sx={{ width: 350, height: 350 }} animation="wave" variant="rectangular" />
  ) : (
    <img
      src={`data:image/jpeg;base64,${attachmentImage}`}
      alt={item.title}
      loading="lazy"
      style={{ width: '100%', height: '100%' }}
    />
  );
}
