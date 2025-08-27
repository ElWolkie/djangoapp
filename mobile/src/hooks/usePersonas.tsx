// src/hooks/usePersonas.ts
import { useState, useEffect } from 'react';
import api from '../api/api';

export interface Persona {
  idPersona: number;
  nombres: string;
  apellidos: string;
  cedula: string;
  telefono: string;
  correo: string;
  rif?: string;
  estadoPersona: 'ACTIVO' | 'INACTIVO';
  fechaPersona: string;
  tipos: { idTP: number; nombreTP: string }[];
}

export const usePersonas = () => {
  const [data, setData]       = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<Error|null>(null);

  useEffect(() => {
    api.get<Persona[]>('/api/personas/')
      .then(res => setData(res.data))
      .catch(err => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
};
