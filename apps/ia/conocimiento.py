"""
Lo que el modelo necesita saber de sgo_new además de las columnas:
cómo se relacionan las tablas y qué significan los códigos.

Las relaciones salen de las consultas del SGO que ya funcionan. Cuando se
confirme un código nuevo con la base, agregarlo en CODIGOS.
"""

RELACIONES = """
Pedidos.ClienteId = Clientes.ClienteId
Pedidos.DivisionId = Divisiones.DivisionId
Pedidos.EstadoPedidoId = EstadosPedido.EstadoPedidoId
Pedidos.TipoPedidoId = TiposPedido.TipoPedidoId
Pedidos.PerfilCandidatoId = PerfilesCandidatos.PerfilCandidatoId
Pedidos.TipoAsignacionId = TiposAsignacion.TipoAsignacionId
Pedidos.MarcaId = Marcas.MarcaId; Pedidos.LineaId = Lineas.LineaId; Pedidos.PracticeAreaId = PracticeAreas.PracticeAreaId; Pedidos.CentroCostoId = CentrosCosto.CentroCostoId
Entrevistas.SituacionLaboralId = SituacionesLaborales.SituacionLaboralId
PedidosPostulante.PedidoId = Pedidos.PedidoId; PedidosPostulante.PostulanteCandidatoId = Candidatos.CandidatoId
Asignaciones.PedidoId = Pedidos.PedidoId
Asignaciones.CandidatoId = Candidatos.CandidatoId
Asignaciones.EstadoAsignacionId = EstadosAsignacion.EstadoAsignacionId
Asignaciones.TipoAsignacionId = TiposAsignacion.TipoAsignacionId
Asignaciones.AsignacionEjecutivoId = EjecutivosCuenta.EjecutivoCuentaId
Asignaciones.CausalBajaId = CausalesBaja.CausalBajaId
HistorialViaticos.AsignacionId = Asignaciones.AsignacionId AND HistorialViaticos.PedidoId = Asignaciones.PedidoId (unir por las dos columnas)
Entrevistas.CandidatoId = Candidatos.CandidatoId
Entrevistas.EntrevistaPedidoId = Pedidos.PedidoId
Entrevistas.EntrevistaPsicologoId = Psicologos.PsicologoId
Entrevistas.EntrevistaCanalPublicacion = CanalesPublicacionAvisos.CanalPublicacionId
OrdenesFacturacion.PedidoId = Pedidos.PedidoId
OrdenesFacturacion.OrdenServicioId = Servicios.ServicioId
OrdenesFacturacion.OrdenMonCod = Monedas.moncod
OrdenesFacturacion.OrdenResponsableId = EjecutivosCuenta.EjecutivoCuentaId
Clientes.SectorActividadId = SectoresActividad.SectorActividadId
Clientes.TipoClienteId = TiposCliente.TipoClienteId
Clientes.EstadoClienteId = EstadosCliente.EstadoClienteId
Clientes.TendenciaId = Tendencias.TendenciaId
Clientes.ClienteRpoEjecutivoId / ClientePrmEjecutivoId / ClienteProEjecutivoId / ClienteIndEjecutivoId / ClienteAdmEjecutivoId = EjecutivosCuenta.EjecutivoCuentaId (ejecutivo de cada línea: RPO, Promociones, Profesional, Industrial, Administrativa)
Candidatos.CandidatoDepartamentoId = Departamentos.DepartamentoId
Candidatos.CandidatoLocalidadId = Localidades.LocalidadId
Candidatos.CandidatoResidenciaId = Paises.PaisId (país de residencia)
Candidatos.CandidatoNacionalidadId = Paises.PaisId (nacionalidad)
Candidatos.PerfilCandidatoId = PerfilesCandidatos.PerfilCandidatoId
Candidatos.NivelEducativoId = NivelesEducativos.NivelEducativoId
Candidatos.EstadoCivilId = EstadosCiviles.EstadoCivilId
Candidatos.SituacionLaboralId = SituacionesLaborales.SituacionLaboralId
Candidatos.CategoriaLibretaConducirId = CategoriasLibretaConducir.CategoriaLibretaConducirId
Candidatos.WebUserId = CandidatosWeb.WebUserId (el candidato vino de la web)
CandidatoPruebas.CandidatoId = Candidatos.CandidatoId; CandidatoPruebas.PruebaId = Pruebas.PruebaId
CandidatosCompetencias.CandidatoId = Candidatos.CandidatoId; CandidatosCompetencias.CompetenciaId = Competencias.CompetenciaId
CandidatosCategoriaProfesional.CandidatoId = Candidatos.CandidatoId; CandidatosCategoriaProfesional.CategoriaProfId = CategoriasProfesionales.CategoriaProfId
CandidatoCheckReferencias.CheckRefPsicologoId = Psicologos.PsicologoId
CandidatosWeb.DepartamentoId = Departamentos.DepartamentoId
CandidatosWeb.LocalidadId = Localidades.LocalidadId
CandidatosWeb.WebUserEstadoCivilId = EstadosCiviles.EstadoCivilId
CVExperiencia.WebUserId / CVFormacion.WebUserId / CVIdiomas.WebUserId / CVAptitudes.WebUserId = CandidatosWeb.WebUserId
CVExperiencia.CausalBajaId = CausalesBaja.CausalBajaId
CVFormacion.CursoId = CursosCarreras.CursoId; CursosCarreras.NivelEducativoId = NivelesEducativos.NivelEducativoId
CVIdiomas.CVIdiomaId = Competencias.CompetenciaId (el idioma)
CVAptitudes.CVAptitudId = Competencias.CompetenciaId (la aptitud)
"""

CODIGOS = """
- Clientes.EstadoClienteId: 2 = Activo (las descripciones están en EstadosCliente: No Especificado, Activo, Descartado, Inactivo, Perdido, Potencial, Potencial Apuntado, Protegido, No Contactar).
- Columnas de una letra Sí/No usan 'S' y 'N' (ClienteOperaAdministrativa, ClienteOperaIndustrial, ClienteOperaProfesional, ClienteOperaPromociones, ClienteOperaRPO, ClienteUtilizaPersonalTemporal).
- Clientes.ClienteRanking está vacío: no usarlo.
- CVExperiencia.CVExpTrabajoActual = 'S' es el trabajo actual (no tiene fecha de egreso).
- CVFormacion.CVFormCompleto: 'C' completa, 'I' incompleta.
- CVIdiomas.CVIdiomaNivel va de 1 (básico) a 5 (nativo/avanzado).
- CandidatosWeb no tiene fecha de alta; WebUserFechaAct es la última actualización del registro.
- Facturación: OrdenesFacturacion.OrdenMonto es el importe; la moneda está en OrdenMonCod (tabla Monedas). No sumar montos de distintas monedas sin separarlos por moneda.
- Pedido entregado a tiempo: PedidoFechaEntregaEfectiva <= PedidoFechaTopeEntrega.
- Pedidos.PedidoFechaCierre vacía se guarda como NULL o como '1900-01-01' / '1753-01-01': pedido abierto = cierre NULL o en esas fechas.
- Pedidos.EstadoPedidoId (como lo usa el SGO): 9 = Finalizado, 8 = Cubierto, 3 = Cancelado, 6 = No cubierto; 7, 2, 4 y 5 son estados abiertos. Mostrar siempre EstadosPedido.EstadoPedidoDescripcion.
- Pedidos.PedidoDerivado y PedidoTraspaso: 'S' / 'N'. PedidoCantidadPersonas = vacantes pedidas.
- Entrevistas.EntrevistaEsGrupal: 'S' grupal, 'N' individual. EntrevistaPuntajeFormacion y EntrevistaPuntajeExperiencia son texto con un número de 1 a 5: usar CAST(... AS FLOAT).
- Candidato contratado después de una entrevista: existe Asignaciones con el mismo CandidatoId y AsignacionFechaIngreso > EntrevistaFecha.
- Viáticos: HistorialViaticos.HistorialViaticosImporte (monto), HistorialViaticosFecha, HistorialViaticosObs (observación).
- Asignación vigente: AsignacionFechaEgreso IS NULL.
- Asignaciones.AsignacionDesempenoNum: 0 sin calificar, 1 Deficiente, 2 Regular, 3 Bueno, 4 Muy bueno, 5 Excelente.
- Asignaciones.AsignacionCalidadTrabajo: 'E' Excelente, 'M' Muy bueno, 'B' Bueno, 'R' Regular, 'D' Deficiente, 'N' o NULL sin calificar.
- Asignaciones.AsignacionVolverContratar = 'S': el cliente lo volvería a contratar. Asignaciones.FormaPagoId = FormasPago.FormaPagoId.
- CandidatoCheckReferencias.CheckRefNivelSeguridad: 'A' Alto, 'M' Medio, 'B' Bajo, 'N' No enviable. CheckRefRecontratar es texto libre.
- CandidatoPruebas.CandidatoPruebaResultado es texto: puede ser una fracción ('21/27', aprueba con 70 sobre 100) o 'Apto', 'Aprobado', 'No apto'...
- PedidosPostulante.EventoId 11 o 12 en el último registro del candidato en el pedido = fue dado de alta (trabajó).
"""
