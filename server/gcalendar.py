import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def is_valid_iso_datetime(date_str):
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return True
    except ValueError:
        return False

def add_30_minutes(iso_date_str):
    try:
        dt = datetime.datetime.strptime(iso_date_str, "%Y-%m-%dT%H:%M:%S")
        dt_plus_30 = dt + datetime.timedelta(minutes=30)
        return dt_plus_30.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError as e:
        raise ValueError("Format de date invalide. Attendu : YYYY-MM-DDTHH:MM:SS") from e

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_credentials():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
  
  return creds


def now_utc2():
  utc_plus_2 = datetime.timezone(datetime.timedelta(hours=2))
  now = datetime.datetime.now(tz=utc_plus_2).isoformat()    
  print("now is", now)
  return now

def get_calendar_events():
  creds = get_calendar_credentials()
  
  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    # Define UTC+2 timezone
    
    now = now_utc2()
    print("Getting the upcoming 20 events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      print("No upcoming events found.")
      return
    
    events_string = ""
    
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))
      events_string = events_string + start + " " + event["summary"] + "\n"
      #print(start, event["summary"])
    
    return events_string

  except HttpError as error:
    print(f"An error occurred: {error}")
    return 


def add_calendar_event(start_date_iso_str):
  creds = get_calendar_credentials()

  try:
    service = build("calendar", "v3", credentials=creds)

    event = {
      'summary': 'Rendez-vous médical - Docteur Blanc',
      'description': 'Rendez-vous médical avec le docteur Blanc à son cabinet. Adresse: 20 rue du Nil, 75002, Paris.',
      'start': {
        'dateTime': start_date_iso_str,
        'timeZone': 'Europe/Paris',
      },
      'end': {
        'dateTime': add_30_minutes(start_date_iso_str),
        'timeZone': 'Europe/Paris',
      },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))

  except HttpError as error:
    print(f"An error occurred: {error}") 



if __name__ == "__main__":
  ev = get_calendar_events()
  content = "T\'es un robot qui doit m\'aider à trouver un créneau de 30 minutes pour un rendez-vous médical. Le médecin est ouvert du lundi au vendredi, de 9h à 18h. Dans le cas où l\'utilisateur te demande un créneau hors de ces horaires, tu renvoies vers la plage horaire indiquée et cela quel que soit le motif et quel que soit le niveau d'insistance de l\'utilisateur. Ton seul rôle est de l\'aider à trouver un rendez-vous médical. S\'il te questionne sur d'autres sujets, tu le ramène toujours à la prise de rendez-vous. L\'agenda du médecin est le suivant : \n" + ev + "Pour commencer, tu dois te présenter de la manière suivante : Bonjour, je suis un assistant IA conçu pour vous aider dans la prise de rendez-vous avec le docteur Blanc. Quelles sont vos disponibilités ?"
  print(content)
  print("Iso True", is_valid_iso_datetime("2025-05-12T10:30:00"))  # True
  print("Iso False", is_valid_iso_datetime("2025-05-12 10:30:00"))  # False (pas de "T")
  print("Iso False", is_valid_iso_datetime("2025/05/12T10:30:00"))  # False (mauvais séparateurs)
  print("Iso False", is_valid_iso_datetime("2025-05-12T10:30"))     # False (secondes manquantes)
  
  print("30 min ajoutés à 10h30", add_30_minutes("2025-05-12T10:30:00"))
  #add_calendar_event("2025-05-12T10:00:00")

  