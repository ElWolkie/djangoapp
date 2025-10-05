// src/types/inscripciones.ts
export type TipoCedula = 'V' | 'J' | 'G' | 'E' | 'P';

export interface TipoFormacion {
  idTF: number;
  nombreTipoFormacion: string;
}

export interface Formacion {
  idFormacion: number;
  nombreFormacion: string;
  idTF: number;
  valorInscripcion: number;
  tieneCuotas: boolean;
  cuotas_activas: boolean;
  cantidad_cuotas: number;
  cuotas_json: string; // JSON string con las cuotas
}

// INTERFAZ CORREGIDA - Eliminar 'valor' y mantener solo 'valorCuota'
export interface Cuota {
  nombreCuota: string;
  valorCuota: number;
}

export interface Cohorte {
  idCohorte: number;
  nombreCohorte: string;
}

export interface Persona {
  idPersona: number;
  cedula: string;
  nombres: string;
  apellidos: string;
}

export interface Inscripcion {
  id: number;
  idInscripcion: number;
  idPersona: Persona;
  idFormacion: Formacion;
  idCohorte: Cohorte;
  fechaInscripcion: string;
  estadoPago: 'PENDIENTE' | 'PARCIAL' | 'PAGADO';
  montoPagado: number;
  montoTotal: number;
  saldoPendiente: number;
  is_active: boolean;
}