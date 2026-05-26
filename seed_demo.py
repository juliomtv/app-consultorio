"""
Script de dados de demonstração — Consultório Duas Médicas
Executa: python seed_demo.py
"""
import random
from datetime import datetime, date, timedelta
from app import create_app
from database import db
from database.models import (User, Professional, Appointment, AppointmentHistory,
                              HealthPlan, InsuranceGuide, FinancialTransaction,
                              Notification, LibraryItem, Document, SystemLog)

app = create_app()

# ── Dados realistas ────────────────────────────────────────────────────────────

NOMES_FEMININOS = [
    "Ana Beatriz Oliveira", "Carla Souza Mendes", "Fernanda Lima Costa",
    "Juliana Rocha Ferreira", "Mariana Santos Alves", "Patrícia Gomes Silva",
    "Renata Pereira Nunes", "Simone Cardoso Borges", "Tatiana Freitas Moura",
    "Vanessa Martins Cruz", "Larissa Andrade Pinto", "Camila Ribeiro Lopes",
    "Gabriela Teixeira Ramos", "Isabela Nascimento Dias", "Letícia Monteiro Sousa",
    "Amanda Correia Farias", "Bianca Azevedo Melo", "Cintia Barbosa Lima",
    "Débora Cavalcante Araújo", "Eduarda Pinheiro Castro",
    "Flávia Nogueira Vieira", "Giovana Cunha Medeiros", "Helena Batista Reis",
    "Ingrid Carvalho Campos", "Jéssica Almeida Teixeira", "Karina Neves Guimarães",
    "Lígia Fontes Macedo", "Mônica Duarte Rodrigues", "Natália Paiva Leal",
    "Odete Magalhães Costa", "Priscila Viana Bezerra", "Queila Ramos Dantas",
    "Regina Lúcia Ferraz", "Sandra Melo Queiroz", "Tânia Cristina Lopes",
    "Úrsula Figueiredo Braga", "Vera Lúcia Santana", "Waleska Campos Sena",
    "Yara Cristine Peixoto", "Zilda Aparecida Gomes", "Alice Moreira Brandão",
    "Brenda Cavalcanti Lima", "Clara Regina Assunção", "Diana Ferreira Siqueira",
    "Elaine Cristina Barros", "Fabiana Rocha Salomão", "Graça Aparecida Tavares",
    "Heloísa Mota Feitosa", "Íris Dantas Carvalho", "Joelma Correia Pinto",
]

TELEFONES = [
    "(11) 98765-4321", "(11) 97654-3210", "(21) 98765-1234", "(21) 97654-4321",
    "(31) 98765-5678", "(31) 97654-6789", "(41) 98765-7890", "(41) 97654-8901",
    "(51) 98765-9012", "(51) 97654-0123", "(61) 98765-1357", "(61) 97654-2468",
    "(71) 98765-3579", "(71) 97654-4680", "(81) 98765-5791", "(81) 97654-6802",
    "(85) 98765-7913", "(85) 97654-8024", "(91) 98765-9135", "(91) 97654-0246",
    "(19) 98765-1111", "(19) 97654-2222", "(47) 98765-3333", "(47) 97654-4444",
    "(48) 98765-5555", "(48) 97654-6666", "(27) 98765-7777", "(27) 97654-8888",
    "(28) 98765-9999", "(28) 97654-0000", "(62) 98765-1010", "(62) 97654-2020",
    "(63) 98765-3030", "(63) 97654-4040", "(65) 98765-5050", "(65) 97654-6060",
    "(67) 98765-7070", "(67) 97654-8080", "(68) 98765-9090", "(68) 97654-0101",
    "(69) 98765-1212", "(69) 97654-2323", "(73) 98765-3434", "(73) 97654-4545",
    "(74) 98765-5656", "(74) 97654-6767", "(75) 98765-7878", "(75) 97654-8989",
    "(77) 98765-9191", "(77) 97654-0202",
]

TIPOS_SANGUE = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

TIPOS_CONSULTA = ["Consulta", "Retorno", "Exame", "Teleconsulta"]
TIPOS_PESOS = [0.45, 0.25, 0.20, 0.10]

MOTIVOS = [
    "Dor abdominal há 3 dias", "Atraso menstrual", "Pré-natal de rotina",
    "Resultado de exame", "Acompanhamento pós-parto", "Planejamento familiar",
    "Corrimento vaginal", "Dor pélvica crônica", "Rastreamento de câncer",
    "Sangramento irregular", "Queda de cabelo e fadiga", "Desconforto urinário",
    "Controle de hormônios", "Prevenção — Papanicolau", "Ultrassonografia pélvica",
    "Revisão pós-cirúrgica", "Colocação de DIU", "Retirada de implante",
    "Segunda opinião", "Consulta de rotina anual",
]

STATUS_PASSADO  = ["completed", "completed", "completed", "cancelled", "no_show"]
STATUS_HOJE     = ["confirmed", "confirmed", "scheduled", "completed"]
STATUS_FUTURO   = ["scheduled", "scheduled", "scheduled", "confirmed"]

HORARIOS = [
    "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "13:30", "14:00", "14:30", "15:00",
    "15:30", "16:00", "16:30", "17:00", "17:30", "18:00",
]


def run():
    with app.app_context():
        print("Limpando dados de demo anteriores...")
        _limpar()

        print("Criando planos de saúde...")
        plans = _criar_planos()

        print("Criando profissionais...")
        profs = _criar_profissionais()

        print("Criando pacientes...")
        patients = _criar_pacientes()

        print("Criando consultas (15 dias passados + hoje + 15 dias futuros)...")
        _criar_consultas(patients, profs, plans)

        print("Criando guias de plano...")
        _criar_guias(patients, plans)

        print("Criando transações financeiras...")
        _criar_financeiro(plans)

        print("Criando itens na biblioteca...")
        _criar_biblioteca()

        print("\nDemo criado com sucesso!")
        print(f"   {len(patients)} pacientes")
        print(f"   {len(profs)} profissionais")
        print(f"   {len(plans)} planos de saúde")
        appts = Appointment.query.count()
        print(f"   {appts} consultas no total")
        print("\nAcesse: http://127.0.0.1:5000")
        print("Admin: admin@consultorio.com / Admin@2024!")


def _limpar():
    """Remove dados de demo sem apagar o admin."""
    # Ordem importa por FK
    SystemLog.query.delete()
    InsuranceGuide.query.delete()
    AppointmentHistory.query.delete()
    Appointment.query.delete()
    FinancialTransaction.query.delete()
    Notification.query.delete()
    Document.query.delete()
    LibraryItem.query.delete()
    # Remove pacientes e profissionais de demo (mantém admin)
    User.query.filter_by(role="patient").delete()
    User.query.filter_by(role="professional").delete()
    Professional.query.delete()
    HealthPlan.query.delete()
    db.session.commit()


def _criar_planos():
    dados = [
        ("Unimed Nacional",   "Unimed",      "305701", 180.00),
        ("Bradesco Saúde Top","Bradesco",     "005711", 210.00),
        ("SulAmérica Clássica","SulAmérica",  "006246", 165.00),
        ("Amil 400",          "Amil",         "396301", 195.00),
        ("Hapvida Plus",      "Hapvida",      "368253", 140.00),
    ]
    plans = []
    for name, operator, ans, value in dados:
        p = HealthPlan(name=name, operator=operator, ans_code=ans,
                       consultation_value=value, is_active=True)
        db.session.add(p)
        plans.append(p)
    db.session.commit()
    return plans


def _criar_profissionais():
    prof_dados = [
        ("Dra. Julia Andrade",   "julia.andrade@consultorio.com",   "Ginecologia",  "CRM", "54321-SP"),
        ("Dra. Roberta Fonseca", "roberta.fonseca@consultorio.com", "Obstetrícia",  "CRM", "67890-SP"),
    ]
    profs = []
    for name, email, specialty, council_type, council_number in prof_dados:
        user = User(name=name, email=email, role="professional", is_active=True)
        user.set_password("Prof@2024!")
        db.session.add(user)
        db.session.flush()
        prof = Professional(user_id=user.id, specialty=specialty,
                            council_type=council_type, council_number=council_number,
                            is_active=True)
        db.session.add(prof)
        db.session.flush()
        profs.append(prof)
    db.session.commit()
    return profs


def _criar_pacientes():
    patients = []
    for i, nome in enumerate(NOMES_FEMININOS):
        email = nome.lower().replace(" ", ".").replace("ã","a").replace("é","e")\
                    .replace("â","a").replace("ê","e").replace("í","i")\
                    .replace("ó","o").replace("ô","o").replace("ú","u")\
                    .replace("ç","c") + f"{i+1}@email.com"
        cpf_num = f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}"
        birth = date(random.randint(1975, 2000), random.randint(1, 12), random.randint(1, 28))
        user = User(
            name=nome,
            email=email,
            cpf=cpf_num,
            phone=TELEFONES[i],
            whatsapp=TELEFONES[i],
            birth_date=birth,
            blood_type=random.choice(TIPOS_SANGUE),
            role="patient",
            is_active=True,
        )
        user.set_password("Paciente@123")
        db.session.add(user)
        patients.append(user)
    db.session.flush()
    db.session.commit()
    return patients


def _criar_consultas(patients, profs, plans):
    today = date.today()
    admin = User.query.filter_by(role="admin").first()
    appts_criados = []

    # ── Passado: 15 dias ──────────────────────────────────────────────────────
    for dias_atras in range(1, 16):
        dia = today - timedelta(days=dias_atras)
        if dia.weekday() >= 5:   # pula fim de semana
            continue

        horarios_dia = HORARIOS.copy()
        random.shuffle(horarios_dia)
        # ~10 por profissional = 20/dia
        for prof in profs:
            slots_usados = set()
            for _ in range(random.randint(8, 11)):
                paciente = random.choice(patients)
                horario  = horarios_dia.pop() if horarios_dia else f"{random.randint(8,17):02d}:00"
                if horario in slots_usados:
                    continue
                slots_usados.add(horario)

                pay_type = random.choices(["particular","convenio","convenio","convenio"],
                                          weights=[40,20,20,20])[0]
                plan     = random.choice(plans) if pay_type == "convenio" else None
                price    = plan.consultation_value if plan else random.choice([200.0, 250.0, 300.0, 350.0])
                status   = random.choice(STATUS_PASSADO)

                appt = Appointment(
                    patient_id=paciente.id,
                    professional_id=prof.id,
                    date=dia, time=horario, duration=30,
                    status=status,
                    type=random.choices(TIPOS_CONSULTA, weights=TIPOS_PESOS)[0],
                    payment_type=pay_type,
                    plan_id=plan.id if plan else None,
                    notes=random.choice(MOTIVOS),
                    price=price,
                    is_paid=(status == "completed"),
                )
                db.session.add(appt)
                db.session.flush()

                history = AppointmentHistory(
                    appointment_id=appt.id, changed_by=admin.id if admin else None,
                    action="created", new_date=dia, new_time=horario, new_status=status,
                )
                db.session.add(history)
                appts_criados.append(appt)

                if status == "completed":
                    _notif_concluida(paciente, appt)

    # ── Hoje: agenda cheia ────────────────────────────────────────────────────
    horarios_hoje = HORARIOS.copy()
    for prof in profs:
        for i, horario in enumerate(horarios_hoje[:10]):
            paciente = patients[i % len(patients)]
            pay_type = random.choices(["particular","convenio"], weights=[35,65])[0]
            plan     = random.choice(plans) if pay_type == "convenio" else None
            price    = plan.consultation_value if plan else random.choice([200.0, 250.0, 300.0])
            status   = random.choice(STATUS_HOJE)

            appt = Appointment(
                patient_id=paciente.id,
                professional_id=prof.id,
                date=today, time=horario, duration=30,
                status=status,
                type=random.choices(TIPOS_CONSULTA, weights=TIPOS_PESOS)[0],
                payment_type=pay_type,
                plan_id=plan.id if plan else None,
                notes=random.choice(MOTIVOS),
                price=price,
                is_paid=(status == "completed"),
            )
            db.session.add(appt)
            db.session.flush()

            history = AppointmentHistory(
                appointment_id=appt.id, changed_by=admin.id if admin else None,
                action="created", new_date=today, new_time=horario, new_status=status,
            )
            db.session.add(history)
            appts_criados.append(appt)

            # Notificação de confirmação para as consultas de hoje
            notif = Notification(
                user_id=paciente.id,
                title="Consulta confirmada para hoje!",
                message=f"Lembrete: sua consulta com {prof.user.name} está agendada para hoje às {horario}.",
                type="appointment",
                appointment_id=appt.id,
            )
            db.session.add(notif)

        # Próximos slots para hoje (11ª em diante)
        for horario in horarios_hoje[10:]:
            paciente = random.choice(patients)
            pay_type = random.choices(["particular","convenio"], weights=[40,60])[0]
            plan     = random.choice(plans) if pay_type == "convenio" else None
            price    = plan.consultation_value if plan else 250.0

            appt = Appointment(
                patient_id=paciente.id, professional_id=prof.id,
                date=today, time=horario, duration=30,
                status="scheduled",
                type=random.choice(TIPOS_CONSULTA),
                payment_type=pay_type,
                plan_id=plan.id if plan else None,
                notes=random.choice(MOTIVOS),
                price=price, is_paid=False,
            )
            db.session.add(appt)
            appts_criados.append(appt)

    # ── Futuro: próximos 15 dias ──────────────────────────────────────────────
    for dias_frente in range(1, 16):
        dia = today + timedelta(days=dias_frente)
        if dia.weekday() >= 5:
            continue
        horarios_f = HORARIOS.copy()
        for prof in profs:
            for _ in range(random.randint(7, 10)):
                if not horarios_f:
                    break
                horario  = horarios_f.pop(random.randrange(len(horarios_f)))
                paciente = random.choice(patients)
                pay_type = random.choices(["particular","convenio"], weights=[40,60])[0]
                plan     = random.choice(plans) if pay_type == "convenio" else None
                price    = plan.consultation_value if plan else random.choice([200.0,250.0,300.0])
                status   = random.choice(STATUS_FUTURO)

                appt = Appointment(
                    patient_id=paciente.id, professional_id=prof.id,
                    date=dia, time=horario, duration=30,
                    status=status,
                    type=random.choices(TIPOS_CONSULTA, weights=TIPOS_PESOS)[0],
                    payment_type=pay_type,
                    plan_id=plan.id if plan else None,
                    notes=random.choice(MOTIVOS),
                    price=price, is_paid=False,
                )
                db.session.add(appt)
                db.session.flush()

                if status == "confirmed":
                    notif = Notification(
                        user_id=paciente.id,
                        title="Consulta confirmada!",
                        message=f"Sua consulta com {prof.user.name} em {dia.strftime('%d/%m/%Y')} às {horario} foi confirmada.",
                        type="appointment", appointment_id=appt.id,
                    )
                    db.session.add(notif)

    db.session.commit()
    return appts_criados


def _notif_concluida(paciente, appt):
    notif = Notification(
        user_id=paciente.id,
        title="Consulta realizada",
        message=f"Sua consulta em {appt.date.strftime('%d/%m/%Y')} foi concluída. Qualquer dúvida, entre em contato.",
        type="success",
        appointment_id=appt.id,
        is_read=random.choice([True, True, False]),
    )
    db.session.add(notif)


def _criar_guias(patients, plans):
    status_list  = ["pending","authorized","authorized","submitted","paid","paid","denied"]
    proc_dados   = [
        ("10101012", "Consulta em Ginecologia"),
        ("10101020", "Consulta em Obstetrícia"),
        ("40801072", "Ultrassonografia Obstétrica"),
        ("40301523", "Papanicolau — Colpocitologia Oncótica"),
        ("40601110", "Colposcopia"),
        ("40801153", "Ultrassonografia Pélvica"),
    ]
    for i, paciente in enumerate(patients[:20]):
        plan = random.choice(plans)
        proc_code, proc_name = random.choice(proc_dados)
        req_val  = plan.consultation_value
        auth_val = req_val * random.choice([0.9, 1.0, 1.0, 1.0])
        status   = random.choice(status_list)
        paid_val = auth_val if status == "paid" else 0.0
        expiry   = date.today() + timedelta(days=random.randint(15, 60))

        guide = InsuranceGuide(
            patient_id=paciente.id,
            plan_id=plan.id,
            guide_number=f"2026{random.randint(1000000,9999999)}",
            authorization_code=f"AUTH{random.randint(100000,999999)}" if status != "pending" else None,
            procedure_code=proc_code,
            procedure_name=proc_name,
            requested_value=req_val,
            authorized_value=auth_val if status != "pending" else 0.0,
            paid_value=paid_val,
            status=status,
            expiry_date=expiry,
        )
        db.session.add(guide)
    db.session.commit()


def _criar_financeiro(plans):
    today = date.today()
    # Receitas dos últimos 30 dias a partir de consultas concluídas
    appts_pagas = (Appointment.query
                   .filter(Appointment.status == "completed", Appointment.is_paid == True)
                   .all())

    for appt in appts_pagas:
        descricao = (f"Consulta — {appt.patient.name if appt.patient else 'Paciente'} "
                     f"({appt.date.strftime('%d/%m/%Y')})")
        tx = FinancialTransaction(
            type="income",
            category="consulta",
            description=descricao,
            amount=appt.price or 200.0,
            status="paid",
            payment_method=("convenio" if appt.payment_type == "convenio" else
                            "pix" if random.random() > 0.5 else "cartao"),
            paid_at=datetime.combine(appt.date, datetime.min.time()),
            appointment_id=appt.id,
        )
        db.session.add(tx)

    # Despesas fixas do mês
    despesas = [
        ("Aluguel consultório",     "aluguel",      3500.0),
        ("Plano de internet",       "despesa_fixa",  250.0),
        ("Material de escritório",  "material",      180.0),
        ("Limpeza / higiene",       "despesa_fixa",  320.0),
        ("Contador",                "despesa_fixa",  600.0),
        ("Sistema de gestão",       "software",      300.0),
    ]
    for desc, cat, valor in despesas:
        tx = FinancialTransaction(
            type="expense", category=cat, description=desc,
            amount=valor, status="paid",
            payment_method="debito",
            paid_at=datetime(today.year, today.month, 5),
        )
        db.session.add(tx)

    db.session.commit()


def _criar_biblioteca():
    itens = [
        ("Guia de Pré-Natal",
         "Tudo que a gestante precisa saber sobre as consultas de pré-natal.",
         "gestante", "cartilha_prenatal.pdf"),
        ("Planejamento Familiar",
         "Métodos contraceptivos: como escolher o mais adequado para você.",
         "saude_feminina", "planejamento_familiar.pdf"),
        ("Papanicolau: tire suas dúvidas",
         "O que é, como se preparar e a importância do exame preventivo.",
         "prevencao", "papanicolau.pdf"),
        ("Amamentação — primeiros passos",
         "Dicas e orientações para uma amamentação saudável e tranquila.",
         "gestante", "amamentacao.pdf"),
        ("Endometriose: entenda a doença",
         "Sintomas, diagnóstico e opções de tratamento disponíveis.",
         "saude_feminina", "endometriose.pdf"),
        ("Menopausa e qualidade de vida",
         "Como atravessar essa fase com saúde e bem-estar.",
         "saude_feminina", "menopausa.pdf"),
    ]
    for title, desc, cat, filename in itens:
        item = LibraryItem(
            title=title, description=desc, category=cat,
            filename=filename,
            file_size=random.randint(200000, 900000),
            is_public=True,
            download_count=random.randint(5, 80),
        )
        db.session.add(item)
    db.session.commit()


if __name__ == "__main__":
    run()
