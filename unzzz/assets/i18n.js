/* unzzz UI localisation: English source text -> zh/ja/fr/de. */
(() => {
  "use strict";

  const LANGS = ["en", "zh", "ja", "fr", "de"];
  const LOCALES = { en: "en-US", zh: "zh-CN", ja: "ja-JP", fr: "fr-FR", de: "de-DE" };
  const STORAGE = "unzzz.lang";

  // English source -> [Chinese, Japanese, French, German]
  const T = {
    "Waking the server…": ["正在唤醒服务器…", "サーバーを起動しています…", "Réveil du serveur…", "Server wird aufgeweckt…"],
    "A server-side alarm clock that refuses to give up quietly.": ["一个不会轻易放弃的服务器端闹钟。", "静かに諦めないサーバー側の目覚まし時計。", "Un réveil côté serveur qui ne s'arrête pas facilement.", "Ein serverseitiger Wecker, der nicht so schnell aufgibt."],
    "Welcome back": ["欢迎回来", "おかえりなさい", "Bon retour", "Willkommen zurück"],
    "Sign in to schedule alarms and manage the household.": ["登录以设置闹钟并管理家庭。", "ログインしてアラームを設定し、家族を管理します。", "Connectez-vous pour programmer des alarmes et gérer le foyer.", "Melde dich an, um Alarme zu planen und den Haushalt zu verwalten."],
    "Admin password": ["管理员密码", "管理者パスワード", "Mot de passe administrateur", "Admin-Passwort"],
    "Sign in": ["登录", "ログイン", "Se connecter", "Anmelden"],
    "First run": ["首次运行", "初回起動", "Premier lancement", "Erste Einrichtung"],
    "Choose the admin password for this alarm server. You will use it to open the control panel.": ["为此闹钟服务器设置管理员密码。你将用它打开控制面板。", "このアラームサーバーの管理者パスワードを設定します。コントロールパネルを開くときに使います。", "Choisissez le mot de passe administrateur de ce serveur. Il ouvrira le panneau de contrôle.", "Lege das Admin-Passwort für diesen Alarmserver fest. Damit öffnest du die Steuerung."],
    "Repeat password": ["重复密码", "パスワードを再入力", "Répéter le mot de passe", "Passwort wiederholen"],
    "Create password": ["创建密码", "パスワードを作成", "Créer le mot de passe", "Passwort erstellen"],
    "· keep this on your local network": ["· 请仅在本地网络中运行", "· ローカルネットワーク内で使用してください", "· gardez-le sur votre réseau local", "· nur im lokalen Netzwerk betreiben"],
    "Alarms": ["闹钟", "アラーム", "Alarmes", "Alarme"],
    "Users": ["用户", "ユーザー", "Utilisateurs", "Benutzer"],
    "Challenges": ["挑战", "チャレンジ", "Défis", "Herausforderungen"],
    "Music": ["音乐", "音楽", "Musique", "Musik"],
    "Special days": ["特殊日期", "特別日", "Jours spéciaux", "Sondertage"],
    "History": ["历史", "履歴", "Historique", "Verlauf"],
    "Settings": ["设置", "設定", "Réglages", "Einstellungen"],
    "Sign out": ["退出登录", "ログアウト", "Se déconnecter", "Abmelden"],
    "Server time": ["服务器时间", "サーバー時刻", "Heure du serveur", "Serverzeit"],
    "Next alarm": ["下一个闹钟", "次のアラーム", "Prochaine alarme", "Nächster Alarm"],
    "Nothing scheduled": ["暂无计划", "予定なし", "Rien de prévu", "Nichts geplant"],
    "+ New alarm": ["+ 新建闹钟", "+ 新しいアラーム", "+ Nouvelle alarme", "+ Neuer Alarm"],
    "0 of 0 people required": ["需要 0 / 0 人", "0 / 0 人の回答が必要", "0 personne sur 0 requise", "0 von 0 Personen erforderlich"],
    "When a challenge alarm rings, each selected user gets a private shortlink — or share the alarm link and QR code.": ["挑战闹钟响起时，每位选中的用户会收到专属短链接，也可以分享闹钟链接和二维码。", "チャレンジアラームが鳴ると、選択した各ユーザーに専用の短縮リンクが届きます。アラームのリンクと QR コードを共有することもできます。", "Quand une alarme défi sonne, chaque utilisateur sélectionné reçoit un lien privé — ou partagez le lien et le QR code de l'alarme.", "Wenn ein Herausforderungsalarm klingelt, erhält jeder ausgewählte Benutzer einen privaten Kurzlink — oder teile den Alarm-Link und QR-Code."],
    "No alarms yet": ["还没有闹钟", "アラームはまだありません", "Aucune alarme", "Noch keine Alarme"],
    "Add a standard alarm, or a challenge that only stops when everyone answers.": ["添加标准闹钟，或添加需要所有人作答才会停止的挑战闹钟。", "標準アラーム、または全員が回答するまで止まらないチャレンジを追加します。", "Ajoutez une alarme standard ou un défi qui ne s'arrête que lorsque tout le monde a répondu.", "Füge einen Standardalarm oder eine Herausforderung hinzu, die erst endet, wenn alle geantwortet haben."],
    "Create the first alarm": ["创建第一个闹钟", "最初のアラームを作成", "Créer la première alarme", "Ersten Alarm erstellen"],
    "Add as many people as you like. Each challenge alarm can select up to six of them, and only those selected people have to answer.": ["可以添加任意数量的用户。每个挑战闹钟最多选择六人，只有被选中的人需要作答。", "好きなだけユーザーを追加できます。各チャレンジアラームは最大 6 人を選べ、選ばれた人だけが回答します。", "Ajoutez autant de personnes que vous voulez. Chaque alarme défi peut en sélectionner jusqu'à six, et seules ces personnes doivent répondre.", "Füge beliebig viele Personen hinzu. Jeder Herausforderungsalarm kann bis zu sechs auswählen; nur diese müssen antworten."],
    "Add a user": ["添加用户", "ユーザーを追加", "Ajouter un utilisateur", "Benutzer hinzufügen"],
    "Add": ["添加", "追加", "Ajouter", "Hinzufügen"],
    "Your own questions and answers. A challenge alarm can use this pool instead of generated arithmetic. Text answers are compared ignoring case and extra spaces.": ["你自己的问题和答案。挑战闹钟可以使用此题库，而不是自动生成的算术题。文本答案比较时忽略大小写和多余空格。", "独自の質問と答え。チャレンジアラームは自動計算の代わりにこのプールを使えます。テキスト回答は大文字小文字と余分な空白を無視して比較されます。", "Vos propres questions et réponses. Une alarme défi peut utiliser cette banque au lieu de calculs générés. Les réponses texte ignorent la casse et les espaces superflus.", "Eigene Fragen und Antworten. Ein Herausforderungsalarm kann diesen Pool statt generierter Rechenaufgaben nutzen. Textantworten werden ohne Beachtung von Groß-/Kleinschreibung und Leerzeichen verglichen."],
    "Type": ["类型", "種類", "Type", "Typ"],
    "Text answer": ["文本答案", "テキスト回答", "Réponse texte", "Textantwort"],
    "Multiple choice": ["选择题", "選択式", "Choix multiple", "Multiple Choice"],
    "Question": ["问题", "質問", "Question", "Frage"],
    "Options ": ["选项 ", "選択肢 ", "Options ", "Optionen "],
    "(one per line, 2–6)": ["（每行一个，2–6 个）", "（1 行に 1 つ、2〜6 個）", "(une par ligne, 2 à 6)", "(eine pro Zeile, 2–6)"],
    "Answer": ["答案", "答え", "Réponse", "Antwort"],
    "Correct answer": ["正确答案", "正解", "Bonne réponse", "Richtige Antwort"],
    "Text answers ignore case and extra spaces.": ["文本答案忽略大小写和多余空格。", "テキスト回答は大文字小文字と余分な空白を無視します。", "Les réponses texte ignorent la casse et les espaces superflus.", "Textantworten ignorieren Groß-/Kleinschreibung und Leerzeichen."],
    "Must exactly match one of the options above.": ["必须与上方其中一个选项完全一致。", "上の選択肢のいずれかと完全に一致する必要があります。", "Doit correspondre exactement à l'une des options ci-dessus.", "Muss genau einer der Optionen oben entsprechen."],
    "Add question": ["添加问题", "質問を追加", "Ajouter la question", "Frage hinzufügen"],
    "Cancel edit": ["取消编辑", "編集をキャンセル", "Annuler la modification", "Bearbeiten abbrechen"],
    "No custom questions yet": ["还没有自定义问题", "カスタム質問はまだありません", "Aucune question personnalisée", "Noch keine eigenen Fragen"],
    "Music": ["音乐", "音楽", "Musique", "Musik"],
    "Upload the sound an alarm should play. The built-in two-tone beep is always available. WAV, MP3, OGG, OGA, FLAC, M4A, AAC and Opus are accepted, up to 25 MB each.": ["上传闹钟播放的声音。内置双音提示音始终可用。支持 WAV、MP3、OGG、OGA、FLAC、M4A、AAC 和 Opus，每个文件最大 25 MB。", "アラームで再生する音をアップロードします。内蔵のツートーン音は常に利用できます。WAV、MP3、OGG、OGA、FLAC、M4A、AAC、Opus に対応（各 25 MB まで）。", "Téléversez le son d'une alarme. Le bip intégré reste toujours disponible. Formats acceptés : WAV, MP3, OGG, OGA, FLAC, M4A, AAC et Opus, jusqu'à 25 Mo.", "Lade den Ton für einen Alarm hoch. Der eingebaute Zweiklang bleibt verfügbar. Unterstützt WAV, MP3, OGG, OGA, FLAC, M4A, AAC und Opus, je bis 25 MB."],
    "Name ": ["名称 ", "名前 ", "Nom ", "Name "],
    "(optional)": ["（可选）", "（任意）", "(facultatif)", "(optional)"],
    "Audio file": ["音频文件", "音声ファイル", "Fichier audio", "Audiodatei"],
    "Upload music": ["上传音乐", "音楽をアップロード", "Téléverser la musique", "Musik hochladen"],
    "Using the built-in beep": ["使用内置提示音", "内蔵音を使用", "Utilisation du bip intégré", "Eingebauter Ton"],
    "Upload a track to give an alarm its own sound.": ["上传曲目，为闹钟设置专属声音。", "曲をアップロードして、アラーム専用の音にできます。", "Téléversez une piste pour donner un son propre à une alarme.", "Lade einen Titel hoch, um einem Alarm einen eigenen Ton zu geben."],
    "Special days": ["特殊日期", "特別日", "Jours spéciaux", "Sondertage"],
    "Calendar name": ["日历名称", "カレンダー名", "Nom du calendrier", "Kalendername"],
    "CSV file": ["CSV 文件", "CSV ファイル", "Fichier CSV", "CSV-Datei"],
    "Import calendar": ["导入日历", "カレンダーをインポート", "Importer le calendrier", "Kalender importieren"],
    "No special-day calendars": ["没有特殊日期日历", "特別日カレンダーはありません", "Aucun calendrier spécial", "Keine Sondertagskalender"],
    "Import a CSV, then select it in an alarm’s Repeat section.": ["导入 CSV，然后在闹钟的重复设置中选择它。", "CSV をインポートし、アラームの繰り返し設定で選択します。", "Importez un CSV, puis sélectionnez-le dans la section Répétition d'une alarme.", "Importiere eine CSV und wähle sie im Wiederholungsbereich eines Alarms."],
    "Recent alarms": ["最近的闹钟", "最近のアラーム", "Alarmes récentes", "Letzte Alarme"],
    "Refresh": ["刷新", "更新", "Actualiser", "Aktualisieren"],
    "The last 30 rings, including who answered and why the sound stopped.": ["最近 30 次响铃，包括谁作答以及声音为何停止。", "直近 30 回の鳴動。誰が回答したか、なぜ止まったかも表示します。", "Les 30 derniers déclenchements, avec les réponses et la raison de l'arrêt.", "Die letzten 30 Klingelvorgänge, inklusive Antworten und Stoppgrund."],
    "When": ["时间", "日時", "Quand", "Wann"],
    "Alarm": ["闹钟", "アラーム", "Alarme", "Alarm"],
    "Mode": ["模式", "モード", "Mode", "Modus"],
    "Result": ["结果", "結果", "Résultat", "Ergebnis"],
    "Answers": ["作答", "回答", "Réponses", "Antworten"],
    "Nothing here yet": ["暂无记录", "まだ何もありません", "Rien pour l'instant", "Noch nichts"],
    "Once an alarm rings, its outcome shows up here.": ["闹钟响过之后，结果会显示在这里。", "アラームが鳴ると、結果がここに表示されます。", "Une fois qu'une alarme sonne, son résultat apparaît ici.", "Sobald ein Alarm klingelt, erscheint das Ergebnis hier."],
    "Time & links": ["时间与链接", "時刻とリンク", "Heure et liens", "Zeit & Links"],
    "Alarms use this timezone, so daylight saving changes are handled by the server.": ["闹钟使用此时区，夏令时变化由服务器处理。", "アラームはこのタイムゾーンを使い、夏時間の変更はサーバーが処理します。", "Les alarmes utilisent ce fuseau horaire ; les changements d'heure sont gérés par le serveur.", "Alarme nutzen diese Zeitzone; Sommerzeitwechsel übernimmt der Server."],
    "Timezone": ["时区", "タイムゾーン", "Fuseau horaire", "Zeitzone"],
    "Public base URL ": ["公开基础 URL ", "公開ベース URL ", "URL publique de base ", "Öffentliche Basis-URL "],
    "Used for the challenge shortlinks. Set this if the panel is reached through a hostname or reverse proxy. Empty means “use the address in the browser”.": ["用于挑战短链接。如果通过主机名或反向代理访问面板，请设置此项。留空表示“使用浏览器中的地址”。", "チャレンジの短縮リンクに使用します。ホスト名やリバースプロキシ経由でパネルを開く場合に設定します。空欄なら「ブラウザのアドレスを使用」します。", "Utilisée pour les liens des défis. À définir si le panneau passe par un nom d'hôte ou un proxy inverse. Vide = « utiliser l'adresse du navigateur ».", "Für die Kurzlinks der Herausforderungen. Setzen, wenn das Panel über Hostname oder Reverse-Proxy erreichbar ist. Leer = „Adresse des Browsers verwenden“."],
    "Save settings": ["保存设置", "設定を保存", "Enregistrer les réglages", "Einstellungen speichern"],
    "Sound": ["声音", "サウンド", "Son", "Ton"],
    "unzzz synthesises its own two-tone WAV and plays uploaded music with the lightest compatible player.": ["unzzz 自行合成双音 WAV，并使用最轻量的兼容播放器播放上传的音乐。", "unzzz は独自のツートーン WAV を生成し、アップロードされた音楽を軽量な対応プレーヤーで再生します。", "unzzz synthétise son propre WAV deux tons et lit la musique téléversée avec le lecteur compatible le plus léger.", "unzzz erzeugt ein eigenes Zweiklang-WAV und spielt hochgeladene Musik mit dem leichtesten kompatiblen Player ab."],
    "Playback device": ["播放设备", "再生デバイス", "Périphérique de lecture", "Wiedergabegerät"],
    "System default": ["系统默认", "システム既定", "Par défaut du système", "Systemstandard"],
    "Detected ALSA PCMs and PulseAudio sinks appear here.": ["检测到的 ALSA PCM 和 PulseAudio 输出会显示在这里。", "検出された ALSA PCM と PulseAudio シンクがここに表示されます。", "Les PCM ALSA et sorties PulseAudio détectés apparaissent ici.", "Erkannte ALSA-PCMs und PulseAudio-Sinks erscheinen hier."],
    "Refresh devices": ["刷新设备", "デバイスを更新", "Actualiser les périphériques", "Geräte aktualisieren"],
    "Play test beep": ["播放测试提示音", "テスト音を再生", "Jouer le bip de test", "Testton abspielen"],
    "Player": ["播放器", "プレーヤー", "Lecteur", "Player"],
    "Status": ["状态", "状態", "État", "Status"],
    "Current password": ["当前密码", "現在のパスワード", "Mot de passe actuel", "Aktuelles Passwort"],
    "New password": ["新密码", "新しいパスワード", "Nouveau mot de passe", "Neues Passwort"],
    "Repeat new password": ["重复新密码", "新しいパスワードを再入力", "Répéter le nouveau mot de passe", "Neues Passwort wiederholen"],
    "Change password": ["更改密码", "パスワードを変更", "Changer le mot de passe", "Passwort ändern"],
    "This server": ["此服务器", "このサーバー", "Ce serveur", "Dieser Server"],
    "Version": ["版本", "バージョン", "Version", "Version"],
    "Data": ["数据", "データ", "Données", "Daten"],
    "Python": ["Python", "Python", "Python", "Python"],
    "stdlib only": ["仅使用标准库", "標準ライブラリのみ", "bibliothèque standard uniquement", "nur Standardbibliothek"],
    "No cloud, no accounts, no third-party packages. Keep it on your LAN; if you expose it to the internet, put HTTPS in front of it.": ["无云端、无账户、无第三方依赖。请仅在局域网使用；若要暴露到互联网，请在前面加上 HTTPS。", "クラウドなし、アカウントなし、サードパーティ製パッケージなし。LAN 内で使用し、インターネットに公開する場合は HTTPS を前段に置いてください。", "Pas de cloud, pas de comptes, pas de paquets tiers. Gardez-le sur votre LAN ; en cas d'exposition à Internet, placez HTTPS devant.", "Keine Cloud, keine Konten, keine Drittanbieter-Pakete. Nur im LAN betreiben; bei Internetzugriff HTTPS davorschalten."],
    "health": ["健康检查", "ヘルス", "état", "Status"],
    "New alarm": ["新建闹钟", "新しいアラーム", "Nouvelle alarme", "Neuer Alarm"],
    "Edit alarm": ["编辑闹钟", "アラームを編集", "Modifier l'alarme", "Alarm bearbeiten"],
    "Close": ["关闭", "閉じる", "Fermer", "Schließen"],
    "Label": ["名称", "ラベル", "Libellé", "Bezeichnung"],
    "Time": ["时间", "時刻", "Heure", "Zeit"],
    "Repeat": ["重复", "繰り返し", "Répétition", "Wiederholung"],
    "Mon": ["周一", "月", "Lun", "Mo"],
    "Tue": ["周二", "火", "Mar", "Di"],
    "Wed": ["周三", "水", "Mer", "Mi"],
    "Thu": ["周四", "木", "Jeu", "Do"],
    "Fri": ["周五", "金", "Ven", "Fr"],
    "Sat": ["周六", "土", "Sam", "Sa"],
    "Sun": ["周日", "日", "Dim", "So"],
    "or once on": ["或仅一次", "または 1 回だけ", "ou une seule fois le", "oder einmal am"],
    "Clear": ["清除", "クリア", "Effacer", "Löschen"],
    "Pick days for a repeating alarm, or a single date. A challenge alarm needs at least one active person.": ["选择重复的星期，或选择单个日期。挑战闹钟至少需要一位启用的用户。", "繰り返す曜日、または 1 回だけの日付を選びます。チャレンジアラームには有効なユーザーが 1 人以上必要です。", "Choisissez des jours pour une alarme répétée, ou une date unique. Un défi nécessite au moins une personne active.", "Wähle Wochentage für einen wiederkehrenden Alarm oder ein einmaliges Datum. Ein Herausforderungsalarm braucht mindestens eine aktive Person."],
    "How does it stop?": ["如何停止？", "どうやって止めますか？", "Comment s'arrête-t-elle ?", "Wie endet er?"],
    "Standard": ["标准", "標準", "Standard", "Standard"],
    "Stop or snooze from this panel.": ["在此面板停止或延后。", "このパネルから停止またはスヌーズします。", "Arrêter ou reporter depuis ce panneau.", "Von diesem Panel aus stoppen oder snoozen."],
    "Challenge": ["挑战", "チャレンジ", "Défi", "Herausforderung"],
    "Selected users answer a question. One user may snooze; several cannot.": ["选中的用户回答问题。单人可延后，多人不可。", "選択したユーザーが質問に回答します。1 人ならスヌーズ可、複数人は不可。", "Les utilisateurs sélectionnés répondent à une question. Un seul peut reporter ; plusieurs non.", "Ausgewählte Benutzer beantworten eine Frage. Bei einer Person ist Snooze erlaubt, bei mehreren nicht."],
    "Who must answer?": ["谁必须作答？", "誰が回答しますか？", "Qui doit répondre ?", "Wer muss antworten?"],
    "Pick 1–6 users. Paused users are skipped when the alarm rings.": ["选择 1–6 位用户。闹钟响起时，已暂停的用户会被跳过。", "1〜6 人を選択。一時停止中のユーザーは鳴動時にスキップされます。", "Choisissez 1 à 6 utilisateurs. Les utilisateurs en pause sont ignorés au déclenchement.", "Wähle 1–6 Benutzer. Pausierte Benutzer werden beim Klingeln übersprungen."],
    "Challenge type": ["挑战类型", "チャレンジの種類", "Type de défi", "Herausforderungstyp"],
    "Generated maths": ["自动算术", "自動計算", "Calculs générés", "Generierte Rechenaufgaben"],
    "Text question": ["文本问题", "テキスト質問", "Question texte", "Textfrage"],
    "Colour match": ["颜色匹配", "色合わせ", "Association de couleurs", "Farbabgleich"],
    "Pattern paint": ["图案涂色", "パターン塗り", "Peinture de motif", "Muster malen"],
    "Arithmetic generated per person.": ["为每个人生成算术题。", "各ユーザーに計算問題を生成します。", "Calculs générés pour chaque personne.", "Rechenaufgabe pro Person generiert."],
    "Finish condition": ["完成条件", "終了条件", "Condition de fin", "Endbedingung"],
    "All selected users": ["所有选中用户", "選択した全員", "Tous les utilisateurs sélectionnés", "Alle ausgewählten Benutzer"],
    "Fixed number": ["固定数量", "指定人数", "Nombre fixe", "Feste Anzahl"],
    "Stop after how many correct answers?": ["答对多少次后停止？", "正解が何回で停止しますか？", "Arrêter après combien de bonnes réponses ?", "Nach wie vielen richtigen Antworten stoppen?"],
    "Difficulty": ["难度", "難易度", "Difficulté", "Schwierigkeit"],
    "(maths / pattern)": ["（算术 / 图案）", "（計算 / パターン）", "(calculs / motif)", "(Rechnen / Muster)"],
    "Easy — warm-up arithmetic": ["简单 — 热身算术", "やさしい — ウォームアップ計算", "Facile — calculs d'échauffement", "Einfach — Aufwärmrechnen"],
    "Normal — two steps": ["普通 — 两步计算", "普通 — 2 ステップ", "Normal — deux étapes", "Normal — zwei Schritte"],
    "Hard — properly awake": ["困难 — 彻底清醒", "むずかしい — しっかり目覚める", "Difficile — bien réveillé", "Schwer — richtig wach"],
    "Public shortlink": ["公开短链接", "公開短縮リンク", "Lien court public", "Öffentlicher Kurzlink"],
    "Random": ["随机", "ランダム", "Aléatoire", "Zufällig"],
    "3–40 characters: a-z, 0-9, - or _. Lowercase only.": ["3–40 个字符：a-z、0-9、- 或 _，仅限小写。", "3〜40 文字：a-z、0-9、-、_。小文字のみ。", "3 à 40 caractères : a-z, 0-9, - ou _. Minuscules uniquement.", "3–40 Zeichen: a-z, 0-9, - oder _. Nur Kleinbuchstaben."],
    "Preview": ["预览", "プレビュー", "Aperçu", "Vorschau"],
    "A QR code appears on the alarm card after saving.": ["保存后，闹钟卡片上会出现二维码。", "保存後、アラームカードに QR コードが表示されます。", "Un QR code apparaît sur la carte de l'alarme après l'enregistrement.", "Nach dem Speichern erscheint ein QR-Code auf der Alarmkarte."],
    "Sound & special days": ["声音与特殊日期", "サウンドと特別日", "Son et jours spéciaux", "Ton & Sondertage"],
    "Alarm music": ["闹钟音乐", "アラーム音楽", "Musique de l'alarme", "Alarmmusik"],
    "Built-in beep": ["内置提示音", "内蔵音", "Bip intégré", "Eingebauter Ton"],
    "Special-days calendar": ["特殊日期日历", "特別日カレンダー", "Calendrier spécial", "Sondertagskalender"],
    "None — use the week pattern": ["无 — 使用星期模式", "なし — 曜日パターンを使用", "Aucun — utiliser le motif hebdomadaire", "Keiner — Wochenmuster verwenden"],
    "Overrides weekdays for dates in the calendar.": ["覆盖日历中日期对应的星期规则。", "カレンダー内の日付の曜日ルールを上書きします。", "Remplace les jours de la semaine pour les dates du calendrier.", "Überschreibt die Wochentage für Daten im Kalender."],
    "Limits": ["限制", "制限", "Limites", "Grenzen"],
    "Snooze minutes": ["延后分钟数", "スヌーズ時間（分）", "Minutes de report", "Snooze-Minuten"],
    "Max snoozes": ["最多延后次数", "最大スヌーズ回数", "Reports maximum", "Max. Snoozes"],
    "Give up after (min)": ["放弃前等待（分）", "諦めるまで（分）", "Abandon après (min)", "Aufgeben nach (Min.)"],
    "Snooze is available for standard alarms and single-user challenges; multi-person challenges must be answered.": ["标准闹钟和单人挑战可以延后；多人挑战必须作答。", "標準アラームと 1 人チャレンジではスヌーズできます。複数人チャレンジは回答が必要です。", "Le report est disponible pour les alarmes standard et les défis à une personne ; les défis à plusieurs doivent être résolus.", "Snooze ist bei Standardalarmen und Ein-Personen-Herausforderungen möglich; Mehrpersonen-Herausforderungen müssen beantwortet werden."],
    "Alarm enabled": ["闹钟启用", "アラーム有効", "Alarme activée", "Alarm aktiviert"],
    "Delete": ["删除", "削除", "Supprimer", "Löschen"],
    "Cancel": ["取消", "キャンセル", "Annuler", "Abbrechen"],
    "Save alarm": ["保存闹钟", "アラームを保存", "Enregistrer l'alarme", "Alarm speichern"],
    "Alarm shortlink": ["闹钟短链接", "アラーム短縮リンク", "Lien court de l'alarme", "Alarm-Kurzlink"],
    "Share this link or show the QR code. Everyone can open it and pick their own name while the alarm rings.": ["分享此链接或出示二维码。闹钟响起时，每个人都可以打开并选择自己的名字。", "このリンクを共有するか QR コードを見せてください。鳴動中は全員が開いて自分の名前を選べます。", "Partagez ce lien ou montrez le QR code. Chacun peut l'ouvrir et choisir son nom pendant la sonnerie.", "Teile diesen Link oder zeige den QR-Code. Während des Klingelns kann jeder ihn öffnen und seinen Namen wählen."],
    "QR code for the alarm shortlink": ["闹钟短链接二维码", "アラーム短縮リンクの QR コード", "QR code du lien court", "QR-Code für den Alarm-Kurzlink"],
    "Copy link": ["复制链接", "リンクをコピー", "Copier le lien", "Link kopieren"],
    "Open page": ["打开页面", "ページを開く", "Ouvrir la page", "Seite öffnen"],
    "Close": ["关闭", "閉じる", "Fermer", "Schließen"],
    "Are you sure?": ["确定吗？", "本当に？", "Êtes-vous sûr ?", "Sicher?"],
    "Confirm": ["确认", "確認", "Confirmer", "Bestätigen"],
    "Paused": ["已暂停", "一時停止", "En pause", "Pausiert"],
    "Ringing": ["响铃中", "鳴動中", "Sonnerie", "Klingelt"],
    "Snoozed": ["已延后", "スヌーズ中", "Reportée", "Gesnoozt"],
    "Ringing right now": ["正在响铃", "今鳴っています", "Sonne maintenant", "Klingelt jetzt"],
    "Snoozed — will ring again": ["已延后 — 将再次响铃", "スヌーズ中 — また鳴ります", "Reportée — sonnera à nouveau", "Gesnoozt — klingelt erneut"],
    "Next ring skipped": ["下次响铃已跳过", "次の鳴動をスキップ", "Prochaine sonnerie ignorée", "Nächstes Klingeln übersprungen"],
    "Skip next": ["跳过下次", "次回をスキップ", "Ignorer la prochaine", "Nächstes überspringen"],
    "Undo skip": ["取消跳过", "スキップを取消", "Annuler l'ignorance", "Überspringen rückgängig"],
    "Ring now": ["立即响铃", "今すぐ鳴らす", "Sonner maintenant", "Jetzt klingeln"],
    "Edit": ["编辑", "編集", "Modifier", "Bearbeiten"],
    "No users yet. Add people in the Users tab first.": ["还没有用户。请先在“用户”标签中添加。", "ユーザーがいません。先に「ユーザー」タブで追加してください。", "Aucun utilisateur. Ajoutez des personnes dans l'onglet Utilisateurs.", "Noch keine Benutzer. Füge sie zuerst im Tab Benutzer hinzu."],
    "paused": ["已暂停", "一時停止", "en pause", "pausiert"],
    "All selected users": ["所有选中用户", "選択した全員", "Tous les utilisateurs sélectionnés", "Alle ausgewählten Benutzer"],
    "The server limit is {n} users. Delete someone to add another.": ["服务器上限为 {n} 位用户。删除一位才能添加。", "サーバー上限は {n} 人です。追加するには誰かを削除してください。", "La limite du serveur est de {n} utilisateurs. Supprimez quelqu'un pour en ajouter.", "Das Serverlimit liegt bei {n} Benutzern. Lösche jemanden, um weitere hinzuzufügen."],
    "No six-person limit here. Each alarm can still select at most {n} users.": ["这里没有六人限制。每个闹钟仍最多选择 {n} 位用户。", "ここでは 6 人制限はありません。各アラームは最大 {n} 人まで選択できます。", "Pas de limite à six ici. Chaque alarme peut toujours sélectionner au plus {n} utilisateurs.", "Hier gibt es kein Sechserlimit. Jeder Alarm kann weiterhin höchstens {n} Benutzer auswählen."],
    "Active": ["启用", "有効", "Actif", "Aktiv"],
    "Pause": ["暂停", "一時停止", "Mettre en pause", "Pausieren"],
    "Resume": ["恢复", "再開", "Reprendre", "Fortsetzen"],
    "Save": ["保存", "保存", "Enregistrer", "Speichern"],
    "Person resumed": ["用户已恢复", "ユーザーを再開しました", "Personne réactivée", "Person wieder aktiviert"],
    "Person paused": ["用户已暂停", "ユーザーを一時停止しました", "Personne mise en pause", "Person pausiert"],
    "Person deleted": ["用户已删除", "ユーザーを削除しました", "Personne supprimée", "Person gelöscht"],
    "Name saved": ["名称已保存", "名前を保存しました", "Nom enregistré", "Name gespeichert"],
    "Name cannot be empty": ["名称不能为空", "名前は空にできません", "Le nom ne peut pas être vide", "Name darf nicht leer sein"],
    "Save question": ["保存问题", "質問を保存", "Enregistrer la question", "Frage speichern"],
    "Add question": ["添加问题", "質問を追加", "Ajouter la question", "Frage hinzufügen"],
    "Question updated": ["问题已更新", "質問を更新しました", "Question mise à jour", "Frage aktualisiert"],
    "Question added": ["问题已添加", "質問を追加しました", "Question ajoutée", "Frage hinzugefügt"],
    "Question deleted": ["问题已删除", "質問を削除しました", "Question supprimée", "Frage gelöscht"],
    "A question and an answer are required.": ["问题和答案都是必填项。", "質問と答えは必須です。", "Une question et une réponse sont requises.", "Frage und Antwort sind erforderlich."],
    "Multiple choice needs 2–6 options, one per line.": ["选择题需要 2–6 个选项，每行一个。", "選択式には 2〜6 個の選択肢が必要です（1 行に 1 つ）。", "Le choix multiple nécessite 2 à 6 options, une par ligne.", "Multiple Choice braucht 2–6 Optionen, eine pro Zeile."],
    "The correct answer must exactly match one option.": ["正确答案必须与其中一个选项完全一致。", "正解は選択肢のいずれかと完全に一致する必要があります。", "La bonne réponse doit correspondre exactement à une option.", "Die richtige Antwort muss genau einer Option entsprechen."],
    "Choose an audio file.": ["请选择音频文件。", "音声ファイルを選択してください。", "Choisissez un fichier audio.", "Wähle eine Audiodatei."],
    "That file is larger than 25 MB.": ["该文件超过 25 MB。", "ファイルが 25 MB を超えています。", "Ce fichier dépasse 25 Mo.", "Diese Datei ist größer als 25 MB."],
    "Uploading…": ["上传中…", "アップロード中…", "Téléversement…", "Wird hochgeladen…"],
    "Music uploaded": ["音乐已上传", "音楽をアップロードしました", "Musique téléversée", "Musik hochgeladen"],
    "Music deleted": ["音乐已删除", "音楽を削除しました", "Musique supprimée", "Musik gelöscht"],
    "Give the calendar a name.": ["请为日历命名。", "カレンダー名を入力してください。", "Donnez un nom au calendrier.", "Gib dem Kalender einen Namen."],
    "Choose a CSV file.": ["请选择 CSV 文件。", "CSV ファイルを選択してください。", "Choisissez un fichier CSV.", "Wähle eine CSV-Datei."],
    "That CSV is too large.": ["该 CSV 太大。", "CSV が大きすぎます。", "Ce CSV est trop volumineux.", "Diese CSV ist zu groß."],
    "Importing…": ["导入中…", "インポート中…", "Importation…", "Wird importiert…"],
    "Calendar imported": ["日历已导入", "カレンダーをインポートしました", "Calendrier importé", "Kalender importiert"],
    "Calendar deleted": ["日历已删除", "カレンダーを削除しました", "Calendrier supprimé", "Kalender gelöscht"],
    "Settings saved": ["设置已保存", "設定を保存しました", "Réglages enregistrés", "Einstellungen gespeichert"],
    "Test beep played": ["测试提示音已播放", "テスト音を再生しました", "Bip de test joué", "Testton abgespielt"],
    "Playback device saved": ["播放设备已保存", "再生デバイスを保存しました", "Périphérique de lecture enregistré", "Wiedergabegerät gespeichert"],
    "Test on server": ["在服务器上测试", "サーバーでテスト", "Tester sur le serveur", "Auf dem Server testen"],
    "Stop": ["停止", "停止", "Arrêter", "Stoppen"],
    "Server test started": ["服务器测试已开始", "サーバーテストを開始しました", "Test serveur démarré", "Servertest gestartet"],
    "Server test stopped": ["服务器测试已停止", "サーバーテストを停止しました", "Test serveur arrêté", "Servertest gestoppt"],
    "Stop the alarm before testing music": ["测试音乐前请先停止闹钟", "音楽をテストする前にアラームを停止してください", "Arrêtez l'alarme avant de tester la musique", "Stoppe den Alarm, bevor du Musik testest"],
    "Music file is missing": ["音乐文件缺失", "音楽ファイルがありません", "Le fichier musical est manquant", "Musikdatei fehlt"],
    "Could not start playback": ["无法开始播放", "再生を開始できません", "Impossible de démarrer la lecture", "Wiedergabe konnte nicht gestartet werden"],
    "error": ["错误", "エラー", "erreur", "Fehler"],
    "Device list refreshed": ["设备列表已刷新", "デバイス一覧を更新しました", "Liste des périphériques actualisée", "Geräteliste aktualisiert"],
    "Playing…": ["播放中…", "再生中…", "Lecture…", "Wird abgespielt…"],
    "New passwords do not match.": ["两次输入的新密码不一致。", "新しいパスワードが一致しません。", "Les nouveaux mots de passe ne correspondent pas.", "Die neuen Passwörter stimmen nicht überein."],
    "Password changed": ["密码已更改", "パスワードを変更しました", "Mot de passe modifié", "Passwort geändert"],
    "Snoozed": ["已延后", "スヌーズしました", "Reportée", "Gesnoozt"],
    "Alarm stopped": ["闹钟已停止", "アラームを停止しました", "Alarme arrêtée", "Alarm gestoppt"],
    "Alarm silenced. Nice work.": ["闹钟已停止，干得漂亮。", "アラームが止まりました。お見事。", "Alarme arrêtée. Bien joué.", "Alarm gestoppt. Gut gemacht."],
    "Alarm enabled": ["闹钟已启用", "アラームを有効にしました", "Alarme activée", "Alarm aktiviert"],
    "Alarm paused": ["闹钟已暂停", "アラームを一時停止しました", "Alarme mise en pause", "Alarm pausiert"],
    "Next ring will be skipped": ["下次响铃将被跳过", "次の鳴動をスキップします", "La prochaine sonnerie sera ignorée", "Nächstes Klingeln wird übersprungen"],
    "Skip cancelled": ["已取消跳过", "スキップを取消しました", "Ignorance annulée", "Überspringen abgebrochen"],
    "Alarm ringing": ["闹钟响铃中", "アラームが鳴っています", "Alarme en sonnerie", "Alarm klingelt"],
    "Shortlink copied": ["短链接已复制", "短縮リンクをコピーしました", "Lien court copié", "Kurzlink kopiert"],
    "Cannot reach the server.": ["无法连接服务器。", "サーバーに接続できません。", "Impossible de joindre le serveur.", "Server nicht erreichbar."],
    "Alarm updated": ["闹钟已更新", "アラームを更新しました", "Alarme mise à jour", "Alarm aktualisiert"],
    "Alarm created": ["闹钟已创建", "アラームを作成しました", "Alarme créée", "Alarm erstellt"],
    "Alarm deleted": ["闹钟已删除", "アラームを削除しました", "Alarme supprimée", "Alarm gelöscht"],
    "Saving…": ["保存中…", "保存中…", "Enregistrement…", "Wird gespeichert…"],
    "Give the alarm a label.": ["请为闹钟命名。", "アラームに名前を付けてください。", "Donnez un nom à l'alarme.", "Gib dem Alarm eine Bezeichnung."],
    "Pick a time.": ["请选择时间。", "時刻を選んでください。", "Choisissez une heure.", "Wähle eine Uhrzeit."],
    "Choose repeat days or a one-time date, not both.": ["请选择重复星期或一次性日期，不能同时选择。", "繰り返し曜日か 1 回だけの日付のどちらかを選んでください。", "Choisissez des jours répétés ou une date unique, pas les deux.", "Wähle Wiederholungstage oder ein einmaliges Datum, nicht beides."],
    "Pick at least one weekday, or a one-time date.": ["请至少选择一个星期或一次性日期。", "曜日を 1 つ以上選ぶか、1 回だけの日付を選んでください。", "Choisissez au moins un jour ou une date unique.", "Wähle mindestens einen Wochentag oder ein einmaliges Datum."],
    "Select at least one user.": ["请至少选择一位用户。", "ユーザーを 1 人以上選択してください。", "Sélectionnez au moins un utilisateur.", "Wähle mindestens einen Benutzer."],
    "An alarm can select at most six users.": ["每个闹钟最多选择六位用户。", "アラームは最大 6 人まで選択できます。", "Une alarme peut sélectionner au plus six utilisateurs.", "Ein Alarm kann höchstens sechs Benutzer auswählen."],
    "Add a question of this type in the Challenges tab first.": ["请先在挑战标签中添加此类型的问题。", "先に「チャレンジ」タブでこの種類の質問を追加してください。", "Ajoutez d'abord une question de ce type dans l'onglet Défis.", "Füge zuerst eine Frage dieses Typs im Tab Herausforderungen hinzu."],
    "The finish target must be between 1 and the number of selected users.": ["完成目标必须在 1 和选中用户数之间。", "終了目標は 1 以上、選択人数以下にしてください。", "L'objectif doit être compris entre 1 et le nombre d'utilisateurs sélectionnés.", "Das Endziel muss zwischen 1 und der Anzahl ausgewählter Benutzer liegen."],
    "Shortlink must be 3-40 characters: a-z, 0-9, - or _.": ["短链接必须为 3–40 个字符：a-z、0-9、- 或 _。", "短縮リンクは 3〜40 文字（a-z、0-9、-、_）です。", "Le lien court doit faire 3 à 40 caractères : a-z, 0-9, - ou _.", "Kurzlink muss 3–40 Zeichen haben: a-z, 0-9, - oder _."],
    "This is what it looks like.": ["效果如下。", "このように表示されます。", "Voici l'aperçu.", "So sieht es aus."],
    "Good morning": ["早上好", "おはようございます", "Bonjour", "Guten Morgen"],
    "Good afternoon": ["下午好", "こんにちは", "Bon après-midi", "Guten Tag"],
    "Good evening": ["晚上好", "こんばんは", "Bonsoir", "Guten Abend"],
    "Wake-up challenge": ["起床挑战", "起床チャレンジ", "Défi du réveil", "Weck-Herausforderung"],
    "Loading…": ["加载中…", "読み込み中…", "Chargement…", "Wird geladen…"],
    "Checking whether the alarm is still ringing.": ["正在检查闹钟是否仍在响。", "アラームがまだ鳴っているか確認しています。", "Vérification de la sonnerie.", "Prüfe, ob der Alarm noch klingelt."],
    "Private one-time link · it only works while the alarm is ringing.": ["私人一次性链接 · 仅在闹钟响铃时有效。", "個人用の 1 回限りリンク · 鳴動中のみ有効です。", "Lien privé à usage unique · valable uniquement pendant la sonnerie.", "Privater Einmal-Link · nur während des Klingelns gültig."],
    "Alarm shortlink": ["闹钟短链接", "アラーム短縮リンク", "Lien court de l'alarme", "Alarm-Kurzlink"],
    "Checking the alarm.": ["正在检查闹钟。", "アラームを確認しています。", "Vérification de l'alarme.", "Alarm wird geprüft."],
    "One shared link for this alarm · each person picks their own name.": ["此闹钟的共享链接 · 每个人选择自己的名字。", "このアラームの共有リンク · 各自が自分の名前を選びます。", "Un lien partagé pour cette alarme · chacun choisit son nom.", "Ein gemeinsamer Link für diesen Alarm · jeder wählt seinen Namen."],
    "Alarm silenced": ["闹钟已停止", "アラーム停止", "Alarme arrêtée", "Alarm gestoppt"],
    "The alarm stopped": ["闹钟已停止", "アラームが止まりました", "L'alarme s'est arrêtée", "Der Alarm wurde beendet"],
    "All clear.": ["一切正常。", "完了です。", "Tout est clair.", "Alles klar."],
    "Too late.": ["太晚了。", "遅すぎました。", "Trop tard.", "Zu spät."],
    "The sound has stopped for everyone.": ["所有人的声音都已停止。", "全員の音が止まりました。", "Le son s'est arrêté pour tout le monde.", "Der Ton ist für alle gestoppt."],
    "You can close this page.": ["你可以关闭此页面。", "このページを閉じてかまいません。", "Vous pouvez fermer cette page.", "Du kannst diese Seite schließen."],
    "That's you done": ["你已完成", "あなたは完了です", "C'est fait pour vous", "Du bist fertig"],
    "This link is now a spectator view of the challenge.": ["此链接现在是挑战的旁观视图。", "このリンクはチャレンジの観覧画面になりました。", "Ce lien est maintenant une vue spectateur du défi.", "Dieser Link zeigt die Herausforderung jetzt als Zuschauer."],
    "Solve the challenge to silence the alarm.": ["完成挑战以停止闹钟。", "チャレンジを解いてアラームを止めてください。", "Résolvez le défi pour arrêter l'alarme.", "Löse die Herausforderung, um den Alarm zu stoppen."],
    "Everyone selected has to answer.": ["所有选中的人都必须作答。", "選択した全員が回答する必要があります。", "Toutes les personnes sélectionnées doivent répondre.", "Alle ausgewählten Personen müssen antworten."],
    "Choose one option first.": ["请先选择一个选项。", "先に選択肢を 1 つ選んでください。", "Choisissez d'abord une option.", "Wähle zuerst eine Option."],
    "Tap a colour first.": ["请先点选一种颜色。", "先に色を選んでください。", "Touchez d'abord une couleur.", "Tippe zuerst eine Farbe an."],
    "Paint at least one cell first.": ["请先涂至少一个格子。", "先に 1 マス以上塗ってください。", "Peignez d'abord au moins une case.", "Male zuerst mindestens ein Feld."],
    "Enter an answer.": ["请输入答案。", "答えを入力してください。", "Saisissez une réponse.", "Gib eine Antwort ein."],
    "Enter a whole number.": ["请输入整数。", "整数を入力してください。", "Saisissez un nombre entier.", "Gib eine ganze Zahl ein."],
    "Checking…": ["检查中…", "確認中…", "Vérification…", "Wird geprüft…"],
    "Could not check the answer. Try again.": ["无法检查答案，请重试。", "答えを確認できません。もう一度お試しください。", "Impossible de vérifier la réponse. Réessayez.", "Antwort konnte nicht geprüft werden. Versuche es erneut."],
    "Not right. Here is a new question.": ["不对，这是新问题。", "不正解です。新しい問題です。", "Incorrect. Voici une nouvelle question.", "Nicht richtig. Hier ist eine neue Frage."],
    "Network error — the answer was not sent. Try again.": ["网络错误 — 答案未发送，请重试。", "ネットワークエラー — 回答は送信されませんでした。再試行してください。", "Erreur réseau — la réponse n'a pas été envoyée. Réessayez.", "Netzwerkfehler — die Antwort wurde nicht gesendet. Versuche es erneut."],
    "Cannot reach the alarm server. Check that you are on the same network and reload.": ["无法连接闹钟服务器。请确认在同一网络并重新加载。", "アラームサーバーに接続できません。同じネットワークか確認して再読み込みしてください。", "Impossible de joindre le serveur. Vérifiez le réseau et rechargez.", "Alarmserver nicht erreichbar. Prüfe das Netzwerk und lade neu."],
    "This shortlink is not valid.": ["此短链接无效。", "この短縮リンクは無効です。", "Ce lien court n'est pas valide.", "Dieser Kurzlink ist ungültig."],
    "Shortlink": ["短链接", "短縮リンク", "Lien court", "Kurzlink"],
    "Hmm.": ["嗯……", "うーん。", "Hmm.", "Hmm."],
    "This link did not work": ["此链接无法使用", "このリンクは使えません", "Ce lien n'a pas fonctionné", "Dieser Link funktioniert nicht"],
    "Target colour": ["目标颜色", "目標の色", "Couleur cible", "Zielfarbe"],
    "Match the swatch": ["匹配色块", "色見本を合わせる", "Associez l'échantillon", "Farbfeld abgleichen"],
    "Target": ["目标", "目標", "Cible", "Ziel"],
    "Your pattern": ["你的图案", "あなたのパターン", "Votre motif", "Dein Muster"],
    "Your answer": ["你的答案", "あなたの答え", "Votre réponse", "Deine Antwort"],
    "Paint the highlighted pattern.": ["涂出高亮图案。", "ハイライトされたパターンを塗ってください。", "Peignez le motif surligné.", "Male das markierte Muster."],
    "Tap the swatch that matches the target.": ["点选与目标匹配的色块。", "目標に合う色見本をタップしてください。", "Touchez l'échantillon qui correspond à la cible.", "Tippe das Farbfeld an, das zum Ziel passt."],
    "Alarm over": ["闹钟结束", "アラーム終了", "Alarme terminée", "Alarm vorbei"],
    "Waiting for others": ["等待其他人", "他の人を待っています", "En attente des autres", "Warte auf andere"],
    "Last alarm silenced": ["上次闹钟已停止", "前回のアラームは停止しました", "Dernière alarme arrêtée", "Letzter Alarm gestoppt"],
    "The last alarm ended": ["上次闹钟已结束", "前回のアラームは終了しました", "La dernière alarme est terminée", "Der letzte Alarm ist beendet"],
    "Enough answers were reached.": ["已达到足够的回答数。", "必要な回答数に達しました。", "Assez de réponses atteintes.", "Genug Antworten erreicht."],
    "Everyone selected answered.": ["所有选中的人都已作答。", "選択した全員が回答しました。", "Toutes les personnes sélectionnées ont répondu.", "Alle ausgewählten Personen haben geantwortet."],
    "Quiet for now.": ["暂时安静。", "今は静かです。", "Silence pour l'instant.", "Im Moment ruhig."],
    "This link will work again when the alarm rings.": ["闹钟再次响起时，此链接会恢复使用。", "アラームが鳴るとこのリンクが再び使えます。", "Ce lien fonctionnera à nouveau quand l'alarme sonnera.", "Dieser Link funktioniert wieder, wenn der Alarm klingelt."],
    "This alarm is quiet.": ["此闹钟当前安静。", "このアラームは静かです。", "Cette alarme est silencieuse.", "Dieser Alarm ist ruhig."],
    "Keep this link — it will work when the alarm rings.": ["保留此链接 — 闹钟响起时会生效。", "このリンクを保存してください — 鳴動時に使えます。", "Gardez ce lien — il fonctionnera à la sonnerie.", "Behalte diesen Link — er funktioniert beim Klingeln."],
    "This alarm is disabled.": ["此闹钟已停用。", "このアラームは無効です。", "Cette alarme est désactivée.", "Dieser Alarm ist deaktiviert."],
    "The alarm is over": ["闹钟已结束", "アラームは終了しました", "L'alarme est terminée", "Der Alarm ist vorbei"],
    "Give it a minute.": ["稍等一分钟。", "少し待ってください。", "Patientez une minute.", "Warte eine Minute."],
    "The alarm is snoozed.": ["闹钟已延后。", "アラームはスヌーズ中です。", "L'alarme est reportée.", "Der Alarm ist gesnoozt."],
    "Who is up?": ["谁起床了？", "誰が起きますか？", "Qui se lève ?", "Wer steht auf?"],
    "Pick your own name to get your question.": ["选择你的名字以获取问题。", "自分の名前を選んで質問を受け取ってください。", "Choisissez votre nom pour recevoir votre question.", "Wähle deinen Namen, um deine Frage zu erhalten."],
    "Alarm quiet": ["闹钟安静", "アラームは静かです", "Alarme silencieuse", "Alarm ruhig"],
    "Wake up": ["起床", "起床", "Réveil", "Aufwachen"],
    "Open": ["打开", "開く", "Ouvrir", "Öffnen"],
    "Copy": ["复制", "コピー", "Copier", "Kopieren"],
    "Copy all": ["全部复制", "すべてコピー", "Tout copier", "Alle kopieren"],
    "answered": ["已作答", "回答済み", "répondu", "beantwortet"],
    "waiting": ["等待中", "待機中", "en attente", "wartet"],
    "Emergency stop": ["紧急停止", "緊急停止", "Arrêt d'urgence", "Notstopp"],
    "Stop alarm": ["停止闹钟", "アラームを停止", "Arrêter l'alarme", "Alarm stoppen"],
    "Cancel snooze": ["取消延后", "スヌーズを取消", "Annuler le report", "Snooze abbrechen"],
    "Link & QR": ["链接与二维码", "リンクと QR", "Lien et QR", "Link & QR"],
    "Alarm ringing": ["闹钟响铃中", "アラームが鳴っています", "Alarme en sonnerie", "Alarm klingelt"],
    "Alarm snoozed": ["闹钟已延后", "アラームはスヌーズ中", "Alarme reportée", "Alarm gesnoozt"],
    "stop it before it gives up": ["在放弃前停止它", "諦める前に止めてください", "arrêtez-la avant l'abandon", "stoppen, bevor er aufgibt"],
    "fired": ["已触发", "鳴動", "déclenchée", "ausgelöst"],
    "gives up": ["放弃", "諦め", "abandonne", "gibt auf"],
    "needed": ["需要", "必要", "requis", "benötigt"],
    "selected": ["已选", "選択", "sélectionné", "ausgewählt"],
    "Somebody": ["某人", "誰か", "Quelqu'un", "Jemand"],
    "Every day": ["每天", "毎日", "Tous les jours", "Täglich"],
    "Weekdays": ["工作日", "平日", "En semaine", "Wochentags"],
    "Weekends": ["周末", "週末", "Week-ends", "Wochenends"],
    "Never": ["从不", "なし", "Jamais", "Nie"],
    "not scheduled": ["未安排", "予定なし", "non planifiée", "nicht geplant"],
    "any moment now": ["马上", "まもなく", "d'un instant à l'autre", "jeden Moment"],
    "in less than a minute": ["不到一分钟", "1 分以内", "dans moins d'une minute", "in weniger als einer Minute"],
    "in {n} min": ["{1} 分钟后", "{1} 分後", "dans {1} min", "in {1} Min."],
    "in {h}h {m}m": ["{1} 小时 {2} 分后", "{1} 時間 {2} 分後", "dans {1} h {2} min", "in {1} Std. {2} Min."],
    "in {d}d {h}h": ["{1} 天 {2} 小时后", "{1} 日 {2} 時間後", "dans {1} j {2} h", "in {1} T {2} Std."],
    "in {m}m {s}s": ["{1} 分 {2} 秒后", "{1} 分 {2} 秒後", "dans {1} min {2} s", "in {1} Min. {2} Sek."],
    "in {s}s": ["{1} 秒后", "{1} 秒後", "dans {1} s", "in {1} Sek."],
    "tomorrow at {time}": ["明天 {1}", "明日 {1}", "demain à {1}", "morgen um {1}"],
    "{date} at {time}": ["{1} {2}", "{1} {2}", "{1} à {2}", "{1} um {2}"],
    "Once on {date}": ["仅一次：{1}", "1 回のみ: {1}", "Une seule fois le {1}", "Einmalig am {1}"],
    "Red": ["红色", "赤", "Rouge", "Rot"],
    "Orange": ["橙色", "オレンジ", "Orange", "Orange"],
    "Yellow": ["黄色", "黄", "Jaune", "Gelb"],
    "Lime": ["青柠色", "ライム", "Citron vert", "Limette"],
    "Green": ["绿色", "緑", "Vert", "Grün"],
    "Teal": ["蓝绿色", "ティール", "Bleu canard", "Blaugrün"],
    "Cyan": ["青色", "シアン", "Cyan", "Cyan"],
    "Blue": ["蓝色", "青", "Bleu", "Blau"],
    "Indigo": ["靛蓝色", "インディゴ", "Indigo", "Indigo"],
    "Violet": ["紫罗兰色", "バイオレット", "Violet", "Violett"],
    "Pink": ["粉色", "ピンク", "Rose", "Rosa"],
    "Brown": ["棕色", "茶色", "Marron", "Braun"],
    "next ring skipped": ["下次响铃已跳过", "次の鳴動をスキップ", "prochaine sonnerie ignorée", "nächstes Klingeln übersprungen"],
    "ready": ["就绪", "準備完了", "prêt", "bereit"],
    "not available": ["不可用", "利用不可", "indisponible", "nicht verfügbar"],
    "Sound unavailable": ["声音不可用", "サウンド利用不可", "Son indisponible", "Ton nicht verfügbar"],
    "Custom": ["自定义", "カスタム", "Personnalisé", "Benutzerdefiniert"],
    "No dates": ["无日期", "日付なし", "Aucune date", "Keine Daten"],
    "work": ["工作", "勤務", "travail", "Arbeit"],
    "working": ["工作", "勤務", "travaillé", "Arbeit"],
    "holiday": ["休息", "休日", "férié", "Feiertag"],
    "Active": ["启用", "有効", "Actif", "Aktiv"],
    "Paused": ["已暂停", "一時停止", "En pause", "Pausiert"],
    "Answered": ["已作答", "回答済み", "Répondu", "Beantwortet"],
    "Stopped": ["已停止", "停止", "Arrêtée", "Gestoppt"],
    "Timed out": ["超时", "タイムアウト", "Expirée", "Zeitüberschreitung"],
    "Interrupted": ["已中断", "中断", "Interrompue", "Unterbrochen"],
    "Missed": ["已错过", "未実行", "Manquée", "Verpasst"],
    "Skipped": ["已跳过", "スキップ", "Ignorée", "Übersprungen"],
    "Completed": ["已完成", "完了", "Terminée", "Abgeschlossen"],
    "expired": ["超时", "タイムアウト", "expirée", "abgelaufen"],
    "interrupted": ["已中断", "中断", "interrompue", "unterbrochen"],
    "missed": ["已错过", "未実行", "manquée", "verpasst"],
    "stopped": ["已停止", "停止", "arrêtée", "gestoppt"],
    "completed": ["已完成", "完了", "terminée", "abgeschlossen"],
    "skipped": ["已跳过", "スキップ", "ignorée", "übersprungen"],
    "Rings again": ["再次响铃", "再び鳴ります", "Sonnera à nouveau", "Klingelt wieder"],
    "soon": ["即将", "まもなく", "bientôt", "bald"],
    "Each person opens their own shortlink and answers the question.": ["每个人打开自己的短链接并回答问题。", "各自が自分の短縮リンクを開いて質問に答えます。", "Chacun ouvre son lien court et répond à la question.", "Jeder öffnet seinen eigenen Kurzlink und beantwortet die Frage."],
    "This single-user challenge can be answered or snoozed from this panel.": ["这个单人挑战可以在此面板作答或延后。", "この 1 人チャレンジはこのパネルから回答またはスヌーズできます。", "Ce défi à une personne peut être résolu ou reporté depuis ce panneau.", "Diese Ein-Personen-Herausforderung kann hier beantwortet oder gesnoozt werden."],
    "All selected users must answer; the sound stops when the last one does.": ["所有选中用户都必须作答；最后一人完成后声音停止。", "選択した全員が回答する必要があります。最後の人が答えると音が止まります。", "Tous les utilisateurs sélectionnés doivent répondre ; le son s'arrête au dernier.", "Alle ausgewählten Benutzer müssen antworten; der Ton stoppt beim letzten."],
    "Stop it from here.": ["从这里停止。", "ここから停止します。", "Arrêtez-la ici.", "Hier stoppen."],
    "Stop it from here, or snooze if you need a few more minutes.": ["从这里停止，或需要更多时间时延后。", "ここから停止するか、数分必要ならスヌーズします。", "Arrêtez-la ici, ou reportez si vous avez besoin de quelques minutes.", "Hier stoppen oder snoozen, wenn du noch ein paar Minuten brauchst."],
    "Each selected user gets a private shortlink.": ["每位选中的用户都会收到专属短链接。", "選択した各ユーザーに専用の短縮リンクが届きます。", "Chaque utilisateur sélectionné reçoit un lien privé.", "Jeder ausgewählte Benutzer erhält einen privaten Kurzlink."],
    "One user must answer; snooze is allowed for this single-user challenge.": ["需要一位用户作答；这个单人挑战允许延后。", "1 人が回答します。この 1 人チャレンジではスヌーズできます。", "Un utilisateur doit répondre ; le report est autorisé pour ce défi solo.", "Ein Benutzer muss antworten; bei dieser Ein-Personen-Herausforderung ist Snooze erlaubt."],
    "All selected users must answer before the sound stops.": ["所有选中用户作答后声音才会停止。", "選択した全員が回答するまで音は止まりません。", "Tous les utilisateurs sélectionnés doivent répondre avant l'arrêt du son.", "Alle ausgewählten Benutzer müssen antworten, bevor der Ton stoppt."],
    "Stop or snooze from the ringing card below.": ["在下方响铃卡片中停止或延后。", "下の鳴動カードから停止またはスヌーズします。", "Arrêtez ou reportez depuis la carte de sonnerie ci-dessous.", "Stoppe oder snooze über die Klingelkarte unten."],
    "Every alarm stops on your command": ["每个闹钟都由你手动停止", "すべてのアラームは手動で停止します", "Chaque alarme s'arrête sur votre ordre", "Jeder Alarm stoppt auf deinen Befehl"],
    "The next scheduled ring will be skipped; following occurrences still run.": ["下次计划响铃将被跳过；之后的仍会执行。", "次回の予定鳴動はスキップされます。以降は通常どおりです。", "La prochaine sonnerie prévue sera ignorée ; les suivantes auront lieu.", "Das nächste geplante Klingeln wird übersprungen; weitere finden statt."],
    "A single-user challenge can be snoozed as well as answered.": ["单人挑战既可以作答，也可以延后。", "1 人チャレンジは回答もスヌーズもできます。", "Un défi à une personne peut être résolu ou reporté.", "Eine Ein-Personen-Herausforderung kann beantwortet oder gesnoozt werden."],
    "Standard alarms stop or snooze from this panel.": ["标准闹钟可在此面板停止或延后。", "標準アラームはこのパネルから停止またはスヌーズできます。", "Les alarmes standard s'arrêtent ou se reportent depuis ce panneau.", "Standardalarme stoppen oder snoozen über dieses Panel."],
    "The sound stops after {n} correct answers ({m} users selected).": ["答对 {n} 次后声音停止（已选 {m} 位用户）。", "正解 {n} 回で音が止まります（{m} 人選択）。", "Le son s'arrête après {n} bonnes réponses ({m} utilisateurs sélectionnés).", "Der Ton stoppt nach {n} richtigen Antworten ({m} Benutzer ausgewählt)."],
    "The sound stops after {n} correct answer; {m} users are selected.": ["答对 {n} 次后声音停止；已选 {m} 位用户。", "正解 {n} 回で音が止まります。{m} 人選択中。", "Le son s'arrête après {n} bonne réponse ; {m} utilisateurs sélectionnés.", "Der Ton stoppt nach {n} richtigen Antwort; {m} Benutzer ausgewählt."],
    "Waiting for {n} more people. The alarm keeps ringing until everyone answers.": ["还需等待 {n} 人。所有人作答前闹钟会一直响。", "あと {n} 人待っています。全員が答えるまで鳴り続けます。", "En attente de {n} personne(s). L'alarme sonne jusqu'à ce que tout le monde réponde.", "Warte auf {n} weitere Person(en). Der Alarm klingelt, bis alle antworten."],
    "Waiting for {n} more answers — it stops after {m}.": ["还需 {n} 个回答 — 达到 {m} 个后停止。", "あと {n} 回答 — {m} 回で停止します。", "En attente de {n} réponse(s) — arrêt après {m}.", "Warte auf {n} weitere Antwort(en) — Stopp nach {m}."],
    "Enough answers were reached. {greeting}, {name}.": ["已达到足够的回答数。{greeting}，{name}。", "必要な回答数に達しました。{greeting}、{name}。", "Assez de réponses atteintes. {greeting}, {name}.", "Genug Antworten erreicht. {greeting}, {name}."],
    "Everyone answered. {greeting}, {name}.": ["所有人都已作答。{greeting}，{name}。", "全員が回答しました。{greeting}、{name}。", "Tout le monde a répondu. {greeting}, {name}.", "Alle haben geantwortet. {greeting}, {name}."],
    "You're up, {name}.": ["轮到你了，{name}。", "{name}、起きてください。", "À vous, {name}.", "Du bist dran, {name}."],
    "Wake up, {name}.": ["起床了，{name}。", "{name}、起きてください。", "Réveillez-vous, {name}.", "Aufwachen, {name}."],
    "The alarm gives up around {time}.": ["闹钟大约在 {time} 放弃。", "アラームは {time} 頃に諦めます。", "L'alarme abandonne vers {time}.", "Der Alarm gibt gegen {time} auf."],
    "The alarm stops after {n} correct answers.": ["答对 {n} 次后闹钟停止。", "正解 {n} 回でアラームが止まります。", "L'alarme s'arrête après {n} bonnes réponses.", "Der Alarm stoppt nach {n} richtigen Antworten."],
    "The alarm stops after {n} correct answer.": ["答对 {n} 次后闹钟停止。", "正解 {n} 回でアラームが止まります。", "L'alarme s'arrête après {n} bonne réponse.", "Der Alarm stoppt nach {n} richtigen Antwort."],
    "Next ring: {text}.": ["下次响铃：{text}。", "次の鳴動: {text}。", "Prochaine sonnerie : {text}.", "Nächstes Klingeln: {text}."],
    "Next ring: {text}": ["下次响铃：{text}", "次の鳴動: {text}", "Prochaine sonnerie : {text}", "Nächstes Klingeln: {text}"],
    "I am {name}": ["我是 {name}", "私は {name}", "Je suis {name}", "Ich bin {name}"],
    "No one is ringing": ["当前没有闹钟响", "鳴っているアラームはありません", "Aucune alarme ne sonne", "Kein Alarm klingelt"],
    "Alarm": ["闹钟", "アラーム", "Alarme", "Alarm"],
    "Format: date,type,note — for example 2026-01-01,holiday,New Year or 2026-01-04,work,Make-up workday. Use work/working for a working day and holiday/rest for a rest day. A header row is optional.": ["格式：date,type,note — 例如 2026-01-01,holiday,New Year 或 2026-01-04,work,Make-up workday。用 work/working 表示工作日，用 holiday/rest 表示休息日。表头行可选。", "形式: date,type,note — 例: 2026-01-01,holiday,New Year または 2026-01-04,work,Make-up workday。work/working は勤務日、holiday/rest は休日です。ヘッダー行は任意です。", "Format : date,type,note — par exemple 2026-01-01,holiday,New Year ou 2026-01-04,work,Make-up workday. Utilisez work/working pour un jour travaillé et holiday/rest pour un jour de repos. La ligne d'en-tête est facultative.", "Format: date,type,note — zum Beispiel 2026-01-01,holiday,New Year oder 2026-01-04,work,Make-up workday. work/working = Arbeitstag, holiday/rest = Ruhetag. Eine Kopfzeile ist optional."],
    "Each person gets a target swatch and four colours to choose from.": ["每个人会看到一个目标色块和四种可选颜色。", "各ユーザーに目標の色見本と 4 色の選択肢が表示されます。", "Chaque personne reçoit un échantillon cible et quatre couleurs.", "Jede Person erhält ein Zielfarbfeld und vier Farben zur Auswahl."],
    "Each person paints a small target pattern; difficulty changes the number of cells.": ["每个人涂出一个小目标图案；难度决定格子数量。", "各ユーザーが小さな目標パターンを塗ります。難易度でマス数が変わります。", "Chaque personne peint un petit motif cible ; la difficulté change le nombre de cases.", "Jede Person malt ein kleines Zielmuster; die Schwierigkeit bestimmt die Anzahl der Felder."],
    "No multiple-choice questions yet — add one in Challenges.": ["还没有选择题 — 请在挑战中添加。", "選択式の質問がまだありません — チャレンジで追加してください。", "Aucune question à choix multiple — ajoutez-en dans Défis.", "Noch keine Multiple-Choice-Fragen — füge eine unter Herausforderungen hinzu."],
    "No text questions yet — add one in Challenges.": ["还没有文本问题 — 请在挑战中添加。", "テキスト質問がまだありません — チャレンジで追加してください。", "Aucune question texte — ajoutez-en dans Défis.", "Noch keine Textfragen — füge eine unter Herausforderungen hinzu."],
    "Wrong password": ["密码错误", "パスワードが違います", "Mot de passe incorrect", "Falsches Passwort"],
    "Please sign in": ["请登录", "ログインしてください", "Veuillez vous connecter", "Bitte anmelden"],
    "Current password is wrong": ["当前密码错误", "現在のパスワードが違います", "Le mot de passe actuel est incorrect", "Aktuelles Passwort ist falsch"],
    "Admin password is already set": ["管理员密码已设置", "管理者パスワードは設定済みです", "Le mot de passe administrateur est déjà défini", "Admin-Passwort ist bereits gesetzt"],
    "Set up an admin password first": ["请先设置管理员密码", "先に管理者パスワードを設定してください", "Définissez d'abord un mot de passe administrateur", "Lege zuerst ein Admin-Passwort fest"],
    "Unknown timezone": ["未知时区", "不明なタイムゾーン", "Fuseau horaire inconnu", "Unbekannte Zeitzone"],
    "Base URL must look like http://host:port": ["基础 URL 必须类似 http://host:port", "ベース URL は http://host:port の形式にしてください", "L'URL de base doit ressembler à http://host:port", "Basis-URL muss wie http://host:port aussehen"],
    "Audio device must be empty or start with alsa:/pulse:": ["音频设备必须为空或以 alsa:/pulse: 开头", "音声デバイスは空欄か alsa:/pulse: で始まる必要があります", "Le périphérique audio doit être vide ou commencer par alsa:/pulse:", "Audiogerät muss leer sein oder mit alsa:/pulse: beginnen"],
    "Question kind must be text or choice": ["问题类型必须是文本或选择题", "質問の種類はテキストまたは選択式です", "Le type de question doit être texte ou choix multiple", "Fragetyp muss Text oder Multiple Choice sein"],
    "Correct answer must exactly match one option": ["正确答案必须与一个选项完全一致", "正解は選択肢の 1 つと完全に一致する必要があります", "La bonne réponse doit correspondre exactement à une option", "Die richtige Antwort muss genau einer Option entsprechen"],
    "This alarm link was not found": ["找不到此闹钟链接", "このアラームリンクは見つかりません", "Ce lien d'alarme est introuvable", "Dieser Alarm-Link wurde nicht gefunden"],
    "This alarm is not ringing right now": ["此闹钟当前未响铃", "このアラームは現在鳴っていません", "Cette alarme ne sonne pas actuellement", "Dieser Alarm klingelt gerade nicht"],
    "This alarm is snoozed; try again when it rings": ["此闹钟已延后；响铃时再试", "このアラームはスヌーズ中です。鳴ったら再試行してください", "Cette alarme est reportée ; réessayez à la sonnerie", "Dieser Alarm ist gesnoozt; versuche es beim Klingeln erneut"],
    "Choose who you are": ["请选择你是谁", "自分が誰かを選んでください", "Choisissez qui vous êtes", "Wähle, wer du bist"],
    "That person is not part of this alarm": ["此人不在该闹钟中", "その人はこのアラームの対象外です", "Cette personne ne fait pas partie de cette alarme", "Diese Person gehört nicht zu diesem Alarm"],
    "This question has already been answered": ["此问题已作答", "この質問は回答済みです", "Cette question a déjà été répondue", "Diese Frage wurde bereits beantwortet"],
    "User not found": ["找不到用户", "ユーザーが見つかりません", "Utilisateur introuvable", "Benutzer nicht gefunden"],
    "Alarm not found": ["找不到闹钟", "アラームが見つかりません", "Alarme introuvable", "Alarm nicht gefunden"],
    "Question not found": ["找不到问题", "質問が見つかりません", "Question introuvable", "Frage nicht gefunden"],
    "Music not found": ["找不到音乐", "音楽が見つかりません", "Musique introuvable", "Musik nicht gefunden"],
    "Calendar not found": ["找不到日历", "カレンダーが見つかりません", "Calendrier introuvable", "Kalender nicht gefunden"],
    "Sound is disabled. Remove UNZZZ_AUDIO_CMD=none to enable it.": ["声音已禁用。移除 UNZZZ_AUDIO_CMD=none 以启用。", "サウンドは無効です。有効にするには UNZZZ_AUDIO_CMD=none を外してください。", "Le son est désactivé. Retirez UNZZZ_AUDIO_CMD=none pour l'activer.", "Ton ist deaktiviert. Entferne UNZZZ_AUDIO_CMD=none, um ihn zu aktivieren."],
    "The custom audio command was not found.": ["找不到自定义音频命令。", "カスタム音声コマンドが見つかりません。", "La commande audio personnalisée est introuvable.", "Der benutzerdefinierte Audiobefehl wurde nicht gefunden."],
    "e.g. What is the name of our cat?": ["例如：我们的猫叫什么名字？", "例: うちの猫の名前は？", "ex. Quel est le nom de notre chat ?", "z. B. Wie heißt unsere Katze?"],
    "e.g. Mochi": ["例如：Mochi", "例: Mochi", "ex. Mochi", "z. B. Mochi"],
    "e.g. Ada": ["例如：Ada", "例: Ada", "ex. Ada", "z. B. Ada"],
    "e.g. Sunrise radio": ["例如：日出电台", "例: 日の出ラジオ", "ex. Radio du lever du soleil", "z. B. Sonnenaufgangsradio"],
    "e.g. Work calendar 2026": ["例如：工作日历 2026", "例: 勤務カレンダー 2026", "ex. Calendrier 2026", "z. B. Arbeitskalender 2026"],
    "Wake up": ["起床", "起床", "Réveil", "Aufwachen"],
    "Shortlink and QR code": ["短链接和二维码", "短縮リンクと QR コード", "Lien court et QR code", "Kurzlink und QR-Code"],
    "Skip the next scheduled ring": ["跳过下次计划响铃", "次回の予定鳴動をスキップ", "Ignorer la prochaine sonnerie prévue", "Nächstes geplantes Klingeln überspringen"],
    "Sections": ["分区", "セクション", "Sections", "Bereiche"],
    "Not ringing right now": ["当前未响铃", "現在は鳴っていません", "Aucune sonnerie en cours", "Klingelt gerade nicht"],
    "not ringing": ["未响铃", "鳴っていません", "ne sonne pas", "klingelt nicht"],
    "Name for {name}": ["{name} 的名称", "{name} の名前", "Nom de {name}", "Name für {name}"],
    "This alarm rings again at {time}. Open this link then to answer.": ["此闹钟将在 {time} 再次响铃。到时打开此链接作答。", "このアラームは {time} に再び鳴ります。その時にこのリンクを開いて回答してください。", "Cette alarme sonnera à nouveau à {time}. Ouvrez ce lien pour répondre.", "Dieser Alarm klingelt um {time} erneut. Öffne dann diesen Link zum Antworten."],
    "Rings again at {time}": ["{time} 再次响铃", "{time} に再び鳴ります", "Sonnera à nouveau à {time}", "Klingelt wieder um {time}"],
    "Rings again soon": ["即将再次响铃", "まもなく再び鳴ります", "Sonnera bientôt à nouveau", "Klingelt bald wieder"],
    "Their answers in past alarms stay in the history. Future challenge alarms will not ask them.": ["他们在过去闹钟中的回答会保留在历史中。未来的挑战闹钟不会再询问他们。", "過去のアラームでの回答は履歴に残ります。今後のチャレンジアラームでは表示されません。", "Leurs réponses restent dans l'historique. Les futurs défis ne les solliciteront plus.", "Ihre Antworten bleiben im Verlauf. Zukünftige Herausforderungen fragen sie nicht mehr."],
    "The file is removed from the server. Alarms using it must be changed first.": ["文件将从服务器删除。使用它的闹钟必须先更改。", "ファイルはサーバーから削除されます。使用中のアラームを先に変更してください。", "Le fichier est supprimé du serveur. Les alarmes qui l'utilisent doivent d'abord être modifiées.", "Die Datei wird vom Server gelöscht. Alarme, die sie nutzen, müssen zuerst geändert werden."],
    "Alarms already using custom questions pick a new one when they ring. This cannot be undone.": ["已使用自定义问题的闹钟会在响铃时选择新问题。此操作无法撤销。", "カスタム質問を使用中のアラームは鳴動時に新しい質問を選びます。元に戻せません。", "Les alarmes utilisant des questions personnalisées en choisiront une nouvelle. Action irréversible.", "Alarme mit eigenen Fragen wählen beim Klingeln eine neue. Nicht rückgängig zu machen."],
    "Alarms using it fall back to their weekday pattern and are rescheduled.": ["使用它的闹钟会回退到星期模式并重新排程。", "使用中のアラームは曜日パターンに戻り、再スケジュールされます。", "Les alarmes concernées reviennent à leur motif hebdomadaire et sont reprogrammées.", "Betroffene Alarme fallen auf ihr Wochenmuster zurück und werden neu geplant."],
    "This overrides the challenge before everyone has answered. It is logged in the history.": ["这会在所有人作答前强制覆盖挑战。此操作会记录在历史中。", "全員が回答する前にチャレンジを上書きします。履歴に記録されます。", "Cela force le défi avant que tout le monde ait répondu. C'est enregistré dans l'historique.", "Dies überschreibt die Herausforderung, bevor alle geantwortet haben. Es wird im Verlauf protokolliert."],
    "Emergency stop?": ["紧急停止？", "緊急停止しますか？", "Arrêt d'urgence ?", "Notstopp?"],
    "Stop anyway": ["仍然停止", "それでも停止", "Arrêter quand même", "Trotzdem stoppen"],
    "Delete this question?": ["删除此问题？", "この質問を削除しますか？", "Supprimer cette question ?", "Diese Frage löschen?"],
    "Delete this track?": ["删除此音乐？", "この曲を削除しますか？", "Supprimer cette piste ?", "Diesen Titel löschen?"],
    "Delete this calendar?": ["删除此日历？", "このカレンダーを削除しますか？", "Supprimer ce calendrier ?", "Diesen Kalender löschen?"],
    "Challenge link lifetime after stop": ["停止后挑战链接保留时间", "停止後のチャレンジリンク保持時間", "Durée de vie des liens après l'arrêt", "Lebensdauer der Challenge-Links nach dem Stopp"],
    "(minutes)": ["（分钟）", "（分）", "(minutes)", "(Minuten)"],
    "Private challenge links and the last-result view stop working this many minutes after an alarm is stopped. 0 expires immediately.": ["闹钟停止后，私人挑战链接和上次结果视图会在这么多分钟后失效。0 表示立即失效。", "アラーム停止後、この分数が経過すると個人用チャレンジリンクと前回結果が無効になります。0 は即時失効です。", "Les liens privés et la vue du dernier résultat cessent de fonctionner après ce délai. 0 = expiration immédiate.", "Private Challenge-Links und die letzte Ergebnisansicht verfallen nach dieser Zeit. 0 = sofort."],
    "This challenge link has expired": ["此挑战链接已过期", "このチャレンジリンクは期限切れです", "Ce lien de défi a expiré", "Dieser Challenge-Link ist abgelaufen"],
    "Link retention must be a number of minutes": ["链接保留时间必须是分钟数", "リンク保持時間は分単位の数値で指定してください", "La durée de conservation doit être un nombre de minutes", "Die Link-Aufbewahrung muss eine Minutenanzahl sein"],
    "Target alarm volume": ["闹钟目标音量", "アラームの目標音量", "Volume cible de l'alarme", "Ziel-Lautstärke für Alarme"],
    "The server sets this system volume when an alarm starts and restores the previous volume when it stops.": ["闹钟开始时服务器会将系统音量设为此值，停止后恢复原音量。", "アラーム開始時にこのシステム音量に設定し、停止時に元の音量へ戻します。", "Le serveur applique ce volume au démarrage de l'alarme et restaure le précédent à l'arrêt.", "Der Server setzt diese Systemlautstärke beim Alarmstart und stellt danach den vorherigen Wert wieder her."],
    "Save target volume": ["保存目标音量", "目標音量を保存", "Enregistrer le volume cible", "Ziel-Lautstärke speichern"],
    "Current volume": ["当前音量", "現在の音量", "Volume actuel", "Aktuelle Lautstärke"],
    "Volume backend": ["音量后端", "音量バックエンド", "Backend de volume", "Lautstärke-Backend"],
    "Unavailable": ["不可用", "利用不可", "Indisponible", "Nicht verfügbar"],
    "Target volume saved": ["目标音量已保存", "目標音量を保存しました", "Volume cible enregistré", "Ziel-Lautstärke gespeichert"],
    "Target volume must be 0-100": ["目标音量必须为 0–100", "目標音量は 0〜100 です", "Le volume cible doit être compris entre 0 et 100", "Ziel-Lautstärke muss 0–100 sein"],
    "Challenges per person": ["每人挑战数", "1 人あたりのチャレンジ数", "Défis par personne", "Herausforderungen pro Person"],
    "Each selected person must pass this many challenges before the alarm can stop.": ["每位选中的人必须通过这么多个挑战后闹钟才会停止。", "選択した各ユーザーがこの数のチャレンジを通過するまでアラームは止まりません。", "Chaque personne sélectionnée doit réussir ce nombre de défis avant l'arrêt.", "Jede ausgewählte Person muss so viele Herausforderungen bestehen, bevor der Alarm endet."],
    "Challenges per person must be between 1 and 10.": ["每人挑战数必须在 1 到 10 之间。", "1 人あたりのチャレンジ数は 1〜10 です。", "Le nombre de défis par personne doit être compris entre 1 et 10.", "Herausforderungen pro Person müssen zwischen 1 und 10 liegen."],
    "Random multiple choice": ["随机选择题", "ランダム選択式", "Choix multiple aléatoire", "Zufällige Multiple Choice"],
    "Random choice": ["随机选择", "ランダム選択", "Choix aléatoire", "Zufällige Auswahl"],
    "Each person paints a small target pattern.": ["每个人涂出一个小目标图案。", "各ユーザーが小さな目標パターンを塗ります。", "Chaque personne peint un petit motif cible.", "Jede Person malt ein kleines Zielmuster."],
    "Import multiple choice": ["导入选择题", "選択式をインポート", "Importer des choix multiples", "Multiple Choice importieren"],
    "Import questions": ["导入问题", "質問をインポート", "Importer les questions", "Fragen importieren"],
    "Importing…": ["导入中…", "インポート中…", "Importation…", "Wird importiert…"],
    "card.each": [" · 每人 {n} 题", " · 各 {n} 問", " · {n} par personne", " · {n} pro Person"],
    "Links": ["链接", "リンク", "Liens", "Links"],
    "Manage public links for enabled alarms. Expiration defaults to six hours after an alarm is disabled or removed; edit it per link.": ["管理已启用闹钟的公开链接。默认在闹钟停用或移除后 6 小时过期；可逐个链接修改。", "有効なアラームの公開リンクを管理します。既定では無効化・削除の 6 時間後に失効します。リンクごとに変更できます。", "Gérez les liens publics des alarmes actives. Ils expirent six heures après la désactivation ou la suppression ; modifiable par lien.", "Öffentliche Links aktiver Alarme verwalten. Standardmäßig 6 Stunden nach Deaktivierung/Entfernen; pro Link änderbar."],
    "Create all-in-one link": ["创建全能链接", "オールインワンリンクを作成", "Créer un lien tout-en-un", "All-in-One-Link erstellen"],
    "No public links": ["没有公开链接", "公開リンクがありません", "Aucun lien public", "Keine öffentlichen Links"],
    "Enable an alarm or create the all-in-one shortcut.": ["启用闹钟或创建全能快捷链接。", "アラームを有効にするか、オールインワンリンクを作成してください。", "Activez une alarme ou créez le raccourci tout-en-un.", "Aktiviere einen Alarm oder erstelle den All-in-One-Link."],
    "All-in-one": ["全能", "オールインワン", "Tout-en-un", "All-in-One"],
    "No expiry": ["无到期时间", "有効期限なし", "Sans expiration", "Kein Ablauf"],
    "Expires: ": ["到期：", "有効期限: ", "Expire : ", "Läuft ab: "],
    "Modify": ["修改", "変更", "Modifier", "Ändern"],
    "Open link": ["打开链接", "リンクを開く", "Ouvrir le lien", "Link öffnen"],
    "Edit link": ["编辑链接", "リンクを編集", "Modifier le lien", "Link bearbeiten"],
    "Edit ": ["编辑 ", "編集 ", "Modifier ", "Bearbeiten "],
    "A shortcut that opens the most recent alarm challenge.": ["快速打开最近一次闹钟挑战的快捷链接。", "最新のアラームチャレンジを開くショートカットです。", "Un raccourci vers le défi d'alarme le plus récent.", "Eine Verknüpfung zum neuesten Alarm-Challenge."],
    "Shortlink": ["短链接", "短縮リンク", "Lien court", "Kurzlink"],
    "Expiration": ["到期时间", "有効期限", "Expiration", "Ablauf"],
    "Leave empty for no expiry. The default is six hours after an alarm is disabled or removed.": ["留空表示永不过期。默认在闹钟停用或移除后 6 小时过期。", "空欄なら無期限。既定では無効化・削除の 6 時間後に失効します。", "Laisser vide pour aucune expiration. Par défaut, six heures après la désactivation ou la suppression.", "Leer = kein Ablauf. Standard: sechs Stunden nach Deaktivierung/Entfernen."],
    "Save link": ["保存链接", "リンクを保存", "Enregistrer le lien", "Link speichern"],
    "Link saved": ["链接已保存", "リンクを保存しました", "Lien enregistré", "Link gespeichert"],
    "All-in-one link deleted": ["全能链接已删除", "オールインワンリンクを削除しました", "Lien tout-en-un supprimé", "All-in-One-Link gelöscht"],
    "Snooze": ["延后", "スヌーズ", "Reporter", "Snoozen"],
    "Stop it from this shortlink or snooze for a few more minutes.": ["通过此短链接停止，或再延后几分钟。", "この短縮リンクから停止するか、数分スヌーズしてください。", "Arrêtez depuis ce lien ou reportez de quelques minutes.", "Über diesen Link stoppen oder einige Minuten snoozen."],
    "Use this link to stop or snooze the alarm.": ["使用此链接停止或延后闹钟。", "このリンクでアラームを停止またはスヌーズします。", "Utilisez ce lien pour arrêter ou reporter l'alarme.", "Mit diesem Link den Alarm stoppen oder snoozen."],
    "This alarm link has expired": ["此闹钟链接已过期", "このアラームリンクは期限切れです", "Ce lien d'alarme a expiré", "Dieser Alarm-Link ist abgelaufen"],
    "This link has expired": ["此链接已过期", "このリンクは期限切れです", "Ce lien a expiré", "Dieser Link ist abgelaufen"],
    "Import a year of working and rest dates for school terms, shift patterns or any non-standard week. A date marked “work” rings even on a Sunday; a date marked “holiday” stays quiet even on a Monday.": ["导入一年中的工作和休息日期，用于学期、轮班或任何非标准周。标记为“work”的日期即使周日也会响；标记为“holiday”的日期即使周一也不会响。", "学期、シフト、その他の変則的な週のために、1 年分の勤務日・休日をインポートします。「work」の日は日曜でも鳴り、「holiday」の日は月曜でも鳴りません。", "Importez une année de jours travaillés et de repos pour les trimestres, les rotations ou toute semaine non standard. Une date « work » sonne même un dimanche ; une date « holiday » reste silencieuse même un lundi.", "Importiere ein Jahr Arbeits- und Ruhetage für Schulzeiten, Schichtpläne oder andere Sonderwochen. Ein „work“-Tag klingelt auch sonntags; ein „holiday“-Tag bleibt auch montags still."],
    "Add a few above, then choose a text or multiple-choice challenge type.": ["先在上方添加几个问题，然后在创建挑战闹钟时选择文本或选择题类型。", "上でいくつか追加し、チャレンジアラーム作成時にテキストまたは選択式を選んでください。", "Ajoutez-en quelques-unes ci-dessus, puis choisissez un type texte ou choix multiple pour un défi.", "Füge oben einige hinzu und wähle dann beim Erstellen eines Herausforderungsalarms Text oder Multiple Choice."],
    "Name": ["名称", "名前", "Nom", "Name"],
    "Options": ["选项", "選択肢", "Options", "Optionen"],
    "Public base URL": ["公开基础 URL", "公開ベース URL", "URL publique de base", "Öffentliche Basis-URL"],
    "When it rings, each selected user gets a private shortlink.": ["响铃时，每位选中的用户都会收到专属短链接。", "鳴動時に選択した各ユーザーへ専用の短縮リンクが届きます。", "À la sonnerie, chaque utilisateur sélectionné reçoit un lien privé.", "Beim Klingeln erhält jeder ausgewählte Benutzer einen privaten Kurzlink."],
    "Using a custom player command. Playback device selection is ignored.": ["正在使用自定义播放器命令。播放设备选择将被忽略。", "カスタムプレーヤーコマンドを使用中。再生デバイスの選択は無視されます。", "Commande de lecteur personnalisée utilisée. La sélection du périphérique est ignorée.", "Benutzerdefinierter Player-Befehl aktiv. Die Geräteauswahl wird ignoriert."],
    "Ring this alarm now?": ["现在就让闹钟响？", "このアラームを今鳴らしますか？", "Faire sonner cette alarme maintenant ?", "Diesen Alarm jetzt klingeln lassen?"],
    "Choose your name. The alarm stops after every selected person.": ["选择你的名字。所有选中的人都作答后闹钟停止。", "自分の名前を選んでください。選択した全員が答えるとアラームが止まります。", "Choisissez votre nom. L'alarme s'arrête après chaque personne sélectionnée.", "Wähle deinen Namen. Der Alarm stoppt, nachdem jede ausgewählte Person geantwortet hat."],
    "Text": ["文本", "テキスト", "Texte", "Text"],
    "all": ["全部", "全員", "tous", "alle"],
    "every selected person": ["所有选中的人", "選択した全員", "chaque personne sélectionnée", "jede ausgewählte Person"],
    "this question": ["此问题", "この質問", "cette question", "diese Frage"],
    "this track": ["此音乐", "この曲", "cette piste", "diesen Titel"],
    "this calendar": ["此日历", "このカレンダー", "ce calendrier", "diesen Kalender"],
    "this person": ["此人", "この人", "cette personne", "diese Person"],
    "Choice": ["选择题", "選択式", "Choix", "Auswahl"],
    "Maths": ["算术", "計算", "Calculs", "Rechnen"],
    "Colour": ["颜色", "色", "Couleur", "Farbe"],
    "Pattern": ["图案", "パターン", "Motif", "Muster"],
    "answered by everyone": ["所有人已作答", "全員回答済み", "répondue par tous", "von allen beantwortet"],
    "answered and silenced": ["已作答并停止", "回答して停止", "répondue et arrêtée", "beantwortet und gestoppt"],
    "stopped by an admin": ["被管理员停止", "管理者が停止", "arrêtée par un administrateur", "von einem Admin gestoppt"],
    "interrupted by a server restart": ["因服务器重启而中断", "サーバー再起動で中断", "interrompue par un redémarrage", "durch Serverneustart unterbrochen"],
    "timed out": ["已超时", "タイムアウト", "expirée", "abgelaufen"],
    "next occurrence skipped": ["已跳过下次", "次の回をスキップ", "prochaine occurrence ignorée", "nächster Termin übersprungen"],
    "everyone answered": ["所有人已作答", "全員回答済み", "tout le monde a répondu", "alle haben geantwortet"],
    "emergency stop": ["紧急停止", "緊急停止", "arrêt d'urgence", "Notstopp"],
    "server restarted": ["服务器已重启", "サーバー再起動", "serveur redémarré", "Server neu gestartet"],
    "server restarted while ringing": ["响铃时服务器已重启", "鳴動中にサーバーが再起動しました", "serveur redémarré pendant la sonnerie", "Server während des Klingelns neu gestartet"],
    "emergency stop by admin": ["管理员紧急停止", "管理者による緊急停止", "arrêt d'urgence par l'administrateur", "Notstopp durch Admin"],
    "stopped from panel": ["从面板停止", "パネルから停止", "arrêtée depuis le panneau", "vom Panel gestoppt"],
    "missed while the server was down": ["服务器离线期间错过", "サーバー停止中に未実行", "manquée pendant l'arrêt du serveur", "verpasst, während der Server aus war"],
    "Stop alarm": ["停止闹钟", "アラームを停止", "Arrêter l'alarme", "Alarm stoppen"],
    "Emergency stop": ["紧急停止", "緊急停止", "Arrêt d'urgence", "Notstopp"],
    "Alarm over · unzzz": ["闹钟结束 · unzzz", "アラーム終了 · unzzz", "Alarme terminée · unzzz", "Alarm vorbei · unzzz"],
    "Alarm quiet · unzzz": ["闹钟安静 · unzzz", "アラームは静か · unzzz", "Alarme silencieuse · unzzz", "Alarm ruhig · unzzz"],
    "Wake up · unzzz": ["起床 · unzzz", "起床 · unzzz", "Réveil · unzzz", "Aufwachen · unzzz"],
    "Waiting for others · unzzz": ["等待其他人 · unzzz", "他の人を待機 · unzzz", "En attente · unzzz", "Warte auf andere · unzzz"],
    "Alarm silenced · unzzz": ["闹钟已停止 · unzzz", "アラーム停止 · unzzz", "Alarme arrêtée · unzzz", "Alarm gestoppt · unzzz"],
    "Alarm snoozed · unzzz": ["闹钟已延后 · unzzz", "アラームはスヌーズ中 · unzzz", "Alarme reportée · unzzz", "Alarm gesnoozt · unzzz"],
    "Wake-up challenge · unzzz": ["起床挑战 · unzzz", "起床チャレンジ · unzzz", "Défi du réveil · unzzz", "Weck-Herausforderung · unzzz"],
    "Alarm · unzzz": ["闹钟 · unzzz", "アラーム · unzzz", "Alarme · unzzz", "Alarm · unzzz"],
    "unzzz — alarm server": ["unzzz — 闹钟服务器", "unzzz — アラームサーバー", "unzzz — serveur d'alarmes", "unzzz — Alarmserver"],
    "Every alarm stops on your command": ["每个闹钟都由你手动停止", "すべてのアラームは手動で停止します", "Chaque alarme s'arrête sur votre ordre", "Jeder Alarm stoppt auf deinen Befehl"],
    "Standard alarm ringing": ["标准闹钟响铃中", "標準アラームが鳴っています", "Alarme standard en sonnerie", "Standardalarm klingelt"],
    "card.all": ["{type} · 已选 {count} 人 · 全部作答", "{type} · {count} 人選択 · 全員回答", "{type} · {count} sélectionné(s) · tous doivent répondre", "{type} · {count} ausgewählt · alle müssen antworten"],
    "card.count": ["{type} · 已选 {count} 人 · 答对 {target} 次后停止", "{type} · {count} 人選択 · 正解 {target} 回で停止", "{type} · {count} sélectionné(s) · arrêt après {target} réponses", "{type} · {count} ausgewählt · Stopp nach {target} Antworten"],
    "card.music": ["音乐 · {name}", "音楽 · {name}", "Musique · {name}", "Musik · {name}"],
    "card.calendar": ["特殊日期 · {name}", "特別日 · {name}", "Jours spéciaux · {name}", "Sondertage · {name}"]
  };

  // English templates use positional placeholders so `fill()` can format them
  // the same way as translated templates.
  const EN_TEMPLATES = {
    "in {n} min": "in {1} min",
    "in {h}h {m}m": "in {1}h {2}m",
    "in {d}d {h}h": "in {1}d {2}h",
    "in {m}m {s}s": "in {1}m {2}s",
    "in {s}s": "in {1}s",
    "tomorrow at {time}": "tomorrow at {1}",
    "{date} at {time}": "{1} at {2}",
    "Once on {date}": "Once on {1}",
  };

  // Dynamic counters and name-bearing sentences.  Each entry: regex + outputs
  // for zh, ja, fr, de with {1}/{2}/... placeholders.
  const PATTERNS = [
    [/^(\d+) total · (\d+) enabled$/, ["共 {1} 个 · {2} 个启用", "全 {1} 件 · {2} 件有効", "{1} au total · {2} activées", "{1} gesamt · {2} aktiv"]],
    [/^(\d+) users · (\d+) active$/, ["{1} 位用户 · {2} 位启用", "{1} ユーザー · {2} 人有効", "{1} utilisateurs · {2} actifs", "{1} Benutzer · {2} aktiv"]],
    [/^(\d+) \/ (\d+) selected$/, ["已选 {1} / {2} 人", "{1} / {2} 人選択", "{1} / {2} sélectionnés", "{1} / {2} ausgewählt"]],
    [/^(\d+) of (\d+) answered$/, ["{1} / {2} 已回答", "{1} / {2} 回答済み", "{1} sur {2} répondu", "{1} von {2} beantwortet"]],
    [/^(\d+) of (\d+) people required$/, ["需要 {1} / {2} 人", "{1} / {2} 人の回答が必要", "{1} personne sur {2} requise", "{1} von {2} Personen erforderlich"]],
    [/^(\d+) of (\d+) needed$/, ["需要 {1} / {2}", "{1} / {2} 必要", "{1} sur {2} requis", "{1} von {2} benötigt"]],
    [/^(\d+)\/(\d+) needed · (\d+) selected$/, ["需要 {1}/{2} · 已选 {3} 人", "{1}/{2} 必要 · {3} 人選択", "{1}/{2} requis · {3} sélectionnés", "{1}/{2} benötigt · {3} ausgewählt"]],
    [/^(\d+)\/(\d+) answered$/, ["{1}/{2} 已回答", "{1}/{2} 回答済み", "{1}/{2} répondu", "{1}/{2} beantwortet"]],
    [/^(\d+) question(s?)$/, ["{1} 个问题", "{1} 件の質問", "{1} question(s)", "{1} Frage(n)"]],
    [/^(\d+) track(s?)$/, ["{1} 首音乐", "{1} 曲", "{1} piste(s)", "{1} Titel"]],
    [/^(\d+) calendar(s?)$/, ["{1} 个日历", "{1} 件のカレンダー", "{1} calendrier(s)", "{1} Kalender"]],
    [/^(\d+) option(s?)$/, ["{1} 个选项", "{1} 個の選択肢", "{1} option(s)", "{1} Option(en)"]],
    [/^(\d+) answer(s?)$/, ["{1} 个回答", "{1} 回答", "{1} réponse(s)", "{1} Antwort(en)"]],
    [/^(\d+) user(s?)$/, ["{1} 位用户", "{1} ユーザー", "{1} utilisateur(s)", "{1} Benutzer"]],
    [/^(\d+) people$/, ["{1} 人", "{1} 人", "{1} personne(s)", "{1} Personen"]],
    [/^(\d+) selected · all must answer$/, ["已选 {1} 人 · 全部作答", "{1} 人選択 · 全員回答", "{1} sélectionné(s) · tous doivent répondre", "{1} ausgewählt · alle müssen antworten"]],
    [/^(\d+) selected · stops after (\d+) answers?$/, ["已选 {1} 人 · 答对 {2} 次后停止", "{1} 人選択 · 正解 {2} 回で停止", "{1} sélectionné(s) · arrêt après {2} réponses", "{1} ausgewählt · Stopp nach {2} Antworten"]],
    [/^(\d+) selected · stops after (\d+)$/, ["已选 {1} 人 · 答对 {2} 次停止", "{1} 人選択 · {2} 回で停止", "{1} sélectionné(s) · arrêt après {2}", "{1} ausgewählt · Stopp nach {2}"]],
    [/^(\d+) users? must answer$/, ["{1} 位用户必须作答", "{1} 人の回答が必要", "{1} utilisateur(s) doivent répondre", "{1} Benutzer müssen antworten"]],
    [/^(\d+) wrong (?:try|tries) — here is a fresh one\.$/, ["错了 {1} 次 — 这是新题。", "{1} 回不正解 — 新しい問題です。", "{1} erreur(s) — voici une nouvelle question.", "{1} Fehlversuch(e) — hier ist eine neue Frage."]],
    [/^(\d+) work$/, ["{1} 天工作", "{1} 日勤務", "{1} jour(s) travaillé(s)", "{1} Arbeitstage"]],
    [/^(\d+) working$/, ["{1} 天工作", "{1} 日勤務", "{1} travaillé(s)", "{1} Arbeitstage"]],
    [/^(\d+) holiday$/, ["{1} 天休息", "{1} 日休日", "{1} férié(s)", "{1} Feiertage"]],
    [/^(\d+) alarm(s?)$/, ["{1} 个闹钟", "{1} 件のアラーム", "{1} alarme(s)", "{1} Alarm(e)"]],
    [/^(\d+) alarms?$/, ["{1} 个闹钟", "{1} 件のアラーム", "{1} alarme(s)", "{1} Alarm(e)"]],
    [/^Custom · (.+)$/, ["自定义 · {1}", "カスタム · {1}", "Personnalisé · {1}", "Benutzerdefiniert · {1}"]],
    [/^(.+) added$/, ["已添加 {1}", "{1} を追加しました", "{1} ajouté", "{1} hinzugefügt"]],
    [/^(.+) deleted$/, ["已删除 {1}", "{1} を削除しました", "{1} supprimé", "{1} gelöscht"]],
    [/^Delete (.+)\?$/, ["删除 {1}？", "{1} を削除しますか？", "Supprimer {1} ?", "{1} löschen?"]],
    [/^Delete this question\?$/, ["删除此问题？", "この質問を削除しますか？", "Supprimer cette question ?", "Diese Frage löschen?"]],
    [/^Delete this track\?$/, ["删除此音乐？", "この曲を削除しますか？", "Supprimer cette piste ?", "Diesen Titel löschen?"]],
    [/^Delete this calendar\?$/, ["删除此日历？", "このカレンダーを削除しますか？", "Supprimer ce calendrier ?", "Diesen Kalender löschen?"]],
    [/^(.+) · shortlink$/, ["{1} · 短链接", "{1} · 短縮リンク", "{1} · lien court", "{1} · Kurzlink"]],
    [/^Music · (.+)$/, ["音乐 · {1}", "音楽 · {1}", "Musique · {1}", "Musik · {1}"]],
    [/^Special days · (.+)$/, ["特殊日期 · {1}", "特別日 · {1}", "Jours spéciaux · {1}", "Sondertage · {1}"]],
    [/^Next ring: (.+)\.$/, ["下次响铃：{1}。", "次の鳴動: {1}。", "Prochaine sonnerie : {1}.", "Nächstes Klingeln: {1}."]],
    [/^in (\d+) min$/, ["{1} 分钟后", "{1} 分後", "dans {1} min", "in {1} Min."]],
    [/^in (\d+)h(?: (\d+)m)?$/, ["{1} 小时{m}", "{1} 時間{m}", "dans {1} h{m}", "in {1} Std.{m}"]],
    [/^in (\d+) day(s?) (\d+)h$/, ["{1} 天 {2} 小时后", "{1} 日 {2} 時間後", "dans {1} jour(s) {2} h", "in {1} Tag(en) {2} Std."]],
    [/^in (\d+)m (\d+)s$/, ["{1} 分 {2} 秒后", "{1} 分 {2} 秒後", "dans {1} min {2} s", "in {1} Min. {2} Sek."]],
    [/^in (\d+)s$/, ["{1} 秒后", "{1} 秒後", "dans {1} s", "in {1} Sek."]],
    [/^tomorrow at (.+)$/, ["明天 {1}", "明日 {1}", "demain à {1}", "morgen um {1}"]],
    [/^(.+) · next ring skipped$/, ["{1} · 下次响铃已跳过", "{1} · 次の鳴動をスキップ", "{1} · prochaine sonnerie ignorée", "{1} · nächstes Klingeln übersprungen"]],
    [/^No sound output: (.+)$/, ["无声音输出：{1}", "音声出力なし: {1}", "Aucune sortie audio : {1}", "Keine Tonausgabe: {1}"]],
    [/^Audio problem: (.+)$/, ["音频问题：{1}", "音声の問題: {1}", "Problème audio : {1}", "Audioproblem: {1}"]],
    [/^The server limit is (\d+) users\. Delete someone to add another\.$/, ["服务器上限为 {1} 位用户。删除一位才能添加。", "サーバー上限は {1} 人です。追加するには誰かを削除してください。", "La limite du serveur est de {1} utilisateurs. Supprimez quelqu'un pour en ajouter.", "Das Serverlimit liegt bei {1} Benutzern. Lösche jemanden, um weitere hinzuzufügen."]],
    [/^No six-person limit here\. Each alarm can still select at most (\d+) users\.$/, ["这里没有六人限制。每个闹钟仍最多选择 {1} 位用户。", "ここでは 6 人制限はありません。各アラームは最大 {1} 人まで選択できます。", "Pas de limite à six ici. Chaque alarme peut toujours sélectionner au plus {1} utilisateurs.", "Hier gibt es kein Sechserlimit. Jeder Alarm kann weiterhin höchstens {1} Benutzer auswählen."]],
    [/^(\d+) \/ (\d+) answered$/, ["{1} / {2} 已回答", "{1} / {2} 回答済み", "{1} / {2} répondu", "{1} / {2} beantwortet"]],
    [/^(\d+)h (\d+)m$/, ["{1} 小时 {2} 分", "{1} 時間 {2} 分", "{1} h {2} min", "{1} Std. {2} Min."]],
    [/^(\d+)m (\d+)s$/, ["{1} 分 {2} 秒", "{1} 分 {2} 秒", "{1} min {2} s", "{1} Min. {2} Sek."]],
    [/^(\d+)s$/, ["{1} 秒", "{1} 秒", "{1} s", "{1} Sek."]],
    [/^(.+) · stop it before it gives up$/, ["{1} · 在放弃前停止", "{1} · 諦める前に停止", "{1} · arrêtez avant l'abandon", "{1} · vor dem Aufgeben stoppen"]],
    [/^fired (.+) · gives up (.+) · (.+)$/, ["{1} 触发 · {2} 放弃 · {3}", "{1} 鳴動 · {2} 諦め · {3}", "déclenchée {1} · abandon {2} · {3}", "ausgelöst {1} · gibt auf {2} · {3}"]],
    [/^fired (.+) · gives up (.+)$/, ["{1} 触发 · {2} 放弃", "{1} 鳴動 · {2} 諦め", "déclenchée {1} · abandon {2}", "ausgelöst {1} · gibt auf {2}"]],
    [/^(.+) will start on the server speaker immediately\.$/, ["{1} 将立即在服务器扬声器上响起。", "{1} がすぐにサーバーのスピーカーで鳴ります。", "{1} commencera immédiatement sur le haut-parleur du serveur.", "{1} startet sofort auf dem Server-Lautsprecher."]],
    [/^Wake up, (.+)\.$/, ["起床了，{1}。", "{1}、起きてください。", "Réveillez-vous, {1}.", "Aufwachen, {1}."]],
    [/^You're up, (.+)\.$/, ["轮到你了，{1}。", "{1}、起きてください。", "À vous, {1}.", "Du bist dran, {1}."]],
    [/^I am (.+)$/, ["我是 {1}", "私は {1}", "Je suis {1}", "Ich bin {1}"]],
    [/^The finish target was reached\. (.+), (.+)\.$/, ["已达到完成目标。{1}，{2}。", "終了目標に達しました。{1}、{2}。", "L'objectif est atteint. {1}, {2}.", "Das Ziel wurde erreicht. {1}, {2}."]],
    [/^Everyone answered\. (.+), (.+)\.$/, ["所有人都已作答。{1}，{2}。", "全員が回答しました。{1}、{2}。", "Tout le monde a répondu. {1}, {2}.", "Alle haben geantwortet. {1}, {2}."]],
    [/^This alarm was (.+) — (.+)\.$/, ["此闹钟{1} — {2}。", "このアラームは{1} — {2}。", "Cette alarme a été {1} — {2}.", "Dieser Alarm wurde {1} — {2}."]],
    [/^This alarm was (.+)\.$/, ["此闹钟{1}。", "このアラームは{1}。", "Cette alarme a été {1}.", "Dieser Alarm wurde {1}."]],
    [/^It was (.+) — (.+)\.$/, ["它{1} — {2}。", "それは{1} — {2}。", "Elle a été {1} — {2}.", "Er wurde {1} — {2}."]],
    [/^It was (.+)\.$/, ["它{1}。", "それは{1}。", "Elle a été {1}.", "Er wurde {1}."]],
    [/^The alarm gives up around (.+)\. (.+)$/, ["闹钟大约会在 {1} 放弃。{2}", "アラームは {1} 頃に諦めます。{2}", "L'alarme abandonne vers {1}. {2}", "Der Alarm gibt gegen {1} auf. {2}"]],
    [/^Each person opens their own shortlink and answers the question\. (.+)$/, ["每个人打开自己的短链接并回答问题。{1}", "各自が自分の短縮リンクを開いて質問に答えます。{1}", "Chacun ouvre son lien court et répond à la question. {1}", "Jeder öffnet seinen Kurzlink und beantwortet die Frage. {1}"]],
    [/^The sound stops after (\d+) correct answers?; (\d+) users are selected\.$/, ["答对 {1} 次后声音停止；已选 {2} 位用户。", "正解 {1} 回で音が止まります。{2} 人選択中。", "Le son s'arrête après {1} bonne(s) réponse(s) ; {2} utilisateurs sélectionnés.", "Der Ton stoppt nach {1} richtigen Antwort(en); {2} Benutzer ausgewählt."]],
    [/^The sound stops after (\d+) correct answers? \((\d+) users selected\)\.$/, ["答对 {1} 次后声音停止（已选 {2} 位用户）。", "正解 {1} 回で音が止まります（{2} 人選択）。", "Le son s'arrête après {1} bonne(s) réponse(s) ({2} utilisateurs sélectionnés).", "Der Ton stoppt nach {1} richtigen Antwort(en) ({2} Benutzer ausgewählt)."]],
    [/^Waiting for (\d+) more answers? — it stops after (\d+)\.$/, ["还需 {1} 个回答 — 达到 {2} 个后停止。", "あと {1} 回答 — {2} 回で停止します。", "En attente de {1} réponse(s) — arrêt après {2}.", "Warte auf {1} weitere Antwort(en) — Stopp nach {2}."]],
    [/^Waiting for (\d+) more people\. The alarm keeps ringing until everyone answers\.$/, ["还需等待 {1} 人。所有人作答前闹钟会一直响。", "あと {1} 人待っています。全員が答えるまで鳴り続けます。", "En attente de {1} personne(s). L'alarme sonne jusqu'à ce que tout le monde réponde.", "Warte auf {1} weitere Person(en). Der Alarm klingelt, bis alle antworten."]],
    [/^(\d+) of (\d+) needed$/, ["需要 {1} / {2}", "{1} / {2} 必要", "{1} sur {2} requis", "{1} von {2} benötigt"]],
    [/^(\d+) of (\d+) answered$/, ["{1} / {2} 已回答", "{1} / {2} 回答済み", "{1} sur {2} répondu", "{1} von {2} beantwortet"]],
    [/^(\d+) of (\d+) people required$/, ["需要 {1} / {2} 人", "{1} / {2} 人の回答が必要", "{1} personne sur {2} requise", "{1} von {2} Personen erforderlich"]],
    [/^(\d+) selected · stops after (\d+)$/, ["已选 {1} 人 · 答对 {2} 次停止", "{1} 人選択 · {2} 回で停止", "{1} sélectionné(s) · arrêt après {2}", "{1} ausgewählt · Stopp nach {2}"]],
    [/^(\d+) users? must answer$/, ["{1} 位用户必须作答", "{1} 人の回答が必要", "{1} utilisateur(s) doivent répondre", "{1} Benutzer müssen antworten"]],
    [/^(\d+) questions?$/, ["{1} 个问题", "{1} 件の質問", "{1} question(s)", "{1} Frage(n)"]],
    [/^(\d+) tracks?$/, ["{1} 首音乐", "{1} 曲", "{1} piste(s)", "{1} Titel"]],
    [/^(\d+) calendars?$/, ["{1} 个日历", "{1} 件のカレンダー", "{1} calendrier(s)", "{1} Kalender"]],
    [/^\((\d+) options\)$/, ["（{1} 个选项）", "（{1} 個の選択肢）", "({1} options)", "({1} Optionen)"]],
    [/^(\d+) correct answers?$/, ["{1} 个正确答案", "{1} 回の正解", "{1} bonnes réponses", "{1} richtige Antworten"]],
    [/^target (\d+)$/, ["目标 {1}", "目標 {1}", "objectif {1}", "Ziel {1}"]],
    [/^Choose your name\. The alarm stops after (.+)\.$/, ["选择你的名字。{1}后闹钟停止。", "名前を選んでください。{1}でアラームが止まります。", "Choisissez votre nom. L'alarme s'arrête après {1}.", "Wähle deinen Namen. Der Alarm stoppt nach {1}."]],
    [/^(\d+) (?:multiple-choice|text) questions? available\.$/, ["有 {1} 个可用问题。", "{1} 件の質問があります。", "{1} question(s) disponible(s).", "{1} Frage(n) verfügbar."]],
    [/^Too many attempts\. Try again in (\d+)s\.$/, ["尝试次数过多。请在 {1} 秒后重试。", "試行回数が多すぎます。{1} 秒後に再試行してください。", "Trop de tentatives. Réessayez dans {1} s.", "Zu viele Versuche. Versuche es in {1} Sek. erneut."]],
    [/^Password must be \d+-\d+ characters$/, ["密码长度必须为 8–200 个字符", "パスワードは 8〜200 文字です", "Le mot de passe doit faire 8 à 200 caractères", "Passwort muss 8–200 Zeichen haben"]],
    [/^New password must be \d+-\d+ characters$/, ["新密码长度必须为 8–200 个字符", "新しいパスワードは 8〜200 文字です", "Le nouveau mot de passe doit faire 8 à 200 caractères", "Neues Passwort muss 8–200 Zeichen haben"]],
    [/^Maximum of (\d+) questions$/, ["最多 {1} 个问题", "質問は最大 {1} 件", "{1} questions maximum", "Höchstens {1} Fragen"]],
    [/^Maximum of (\d+) music files$/, ["最多 {1} 个音乐文件", "音楽ファイルは最大 {1} 件", "{1} fichiers audio maximum", "Höchstens {1} Audiodateien"]],
    [/^Maximum of (\d+) calendars$/, ["最多 {1} 个日历", "カレンダーは最大 {1} 件", "{1} calendriers maximum", "Höchstens {1} Kalender"]],
    [/^File is too large \(maximum (\d+) MB\)$/, ["文件太大（最大 {1} MB）", "ファイルが大きすぎます（最大 {1} MB）", "Fichier trop volumineux (maximum {1} Mo)", "Datei zu groß (maximal {1} MB)"]],
    [/^Playing through (.+) \((.+)\)\. Use the test button to verify\.$/, ["通过 {1}（{2}）播放。可使用测试按钮验证。", "{1}（{2}）で再生します。テストボタンで確認してください。", "Lecture via {1} ({2}). Utilisez le bouton de test.", "Wiedergabe über {1} ({2}). Mit der Testtaste prüfen."]],
    [/^Snooze (\d+) min \((\d+) left\)$/, ["延后 {1} 分钟（剩 {2} 次）", "{1} 分スヌーズ（残り {2} 回）", "Reporter {1} min ({2} restants)", "{1} Min. snoozen ({2} übrig)"]],
    [/^Rings again at (.+)$/, ["{1} 再次响铃", "{1} に再び鳴ります", "Sonnera à nouveau à {1}", "Klingelt wieder um {1}"]],
    [/^Rings again soon$/, ["即将再次响铃", "まもなく再び鳴ります", "Sonnera bientôt à nouveau", "Klingelt bald wieder"]],
    [/^This alarm rings again at (.+)\. Open this link then to answer\.$/, ["此闹钟将在 {1} 再次响铃。到时打开此链接作答。", "このアラームは {1} に再び鳴ります。その時にこのリンクを開いて回答してください。", "Cette alarme sonnera à nouveau à {1}. Ouvrez ce lien pour répondre.", "Dieser Alarm klingelt um {1} erneut. Öffne dann diesen Link zum Antworten."]],
    [/^Next ring: (.+)\.$/, ["下次响铃：{1}。", "次の鳴動: {1}。", "Prochaine sonnerie : {1}.", "Nächstes Klingeln: {1}."]],
    [/^target (\d+)$/, ["目标 {1}", "目標 {1}", "objectif {1}", "Ziel {1}"]],
    [/^Choose your name\. The alarm stops after (.+)\.$/, ["选择你的名字。{1}后闹钟停止。", "名前を選んでください。{1}でアラームが止まります。", "Choisissez votre nom. L'alarme s'arrête après {1}.", "Wähle deinen Namen. Der Alarm stoppt nach {1}."]],
    [/^missed: server was not running \((\d+)s late\)$/, ["错过：服务器未运行（晚了 {1} 秒）", "未実行: サーバー停止中（{1} 秒遅れ）", "manquée : serveur arrêté ({1} s de retard)", "verpasst: Server war nicht aktiv ({1} s zu spät)"]],
    [/^Link retention must be 0-(\d+) minutes$/, ["链接保留时间必须为 0–{1} 分钟", "リンク保持時間は 0〜{1} 分です", "La durée de conservation doit être comprise entre 0 et {1} minutes", "Link-Aufbewahrung muss 0–{1} Minuten sein"]],
    [/^A random sequence from (\d+) multiple-choice questions is shared by the session\.$/, ["将从 {1} 道选择题中随机抽取一组题目，供本次会话共用。", "{1} 問の選択式からランダムな問題列を作成し、セッション全員で共有します。", "Une séquence aléatoire de {1} questions à choix multiple est partagée par la session.", "Eine zufällige Folge aus {1} Multiple-Choice-Fragen wird für die Sitzung geteilt."]],
    [/^Each person must pass (\d+) challenges\.$/, ["每个人必须通过 {1} 个挑战。", "各ユーザーは {1} 個のチャレンジを通過する必要があります。", "Chaque personne doit réussir {1} défis.", "Jede Person muss {1} Herausforderungen bestehen."]],
    [/^Correct — (\d+)\/(\d+) challenges passed\.$/, ["正确 — 已通过 {1}/{2} 个挑战。", "正解 — {1}/{2} チャレンジ通過。", "Correct — {1}/{2} défis réussis.", "Richtig — {1}/{2} Herausforderungen bestanden."]],
    [/^(\d+)\/(\d+) passed$/, ["已通过 {1}/{2}", "{1}/{2} 通過", "{1}/{2} réussis", "{1}/{2} bestanden"]],
    [/^(\d+) questions? imported$/, ["已导入 {1} 个问题", "{1} 件の質問をインポートしました", "{1} question(s) importée(s)", "{1} Frage(n) importiert"]],
    [/^Import would exceed the maximum of (\d+) questions$/, ["导入后将超过最多 {1} 个问题的限制", "インポートすると最大 {1} 件の質問を超えます", "L'import dépasserait le maximum de {1} questions", "Der Import würde das Maximum von {1} Fragen überschreiten"]],
    [/^(\d+) links?$/, ["{1} 个链接", "{1} 件のリンク", "{1} lien(s)", "{1} Link(s)"]],
    [/^Expires: (.+)$/, ["到期：{1}", "有効期限: {1}", "Expire : {1}", "Läuft ab: {1}"]],
    [/^This alarm rings again at (.+)\.$/, ["此闹钟将在 {1} 再次响铃。", "このアラームは {1} に再び鳴ります。", "Cette alarme sonnera à nouveau à {1}.", "Dieser Alarm klingelt um {1} erneut."]],
  ];

  const SKIP = [
    "SCRIPT", "STYLE", "TEXTAREA", "PRE", "CODE", "NOSCRIPT",
    "[data-i18n-skip]", ".brand", ".alarm-label", ".user-name", ".track-name",
    ".calendar-name", ".question-text", ".answer-text", ".p-name", ".choice-option",
    ".pick-user > span", ".who", ".slug-preview", "#link-url", "#alarm-label"
  ].join(",");

  function detectLang() {
    const saved = localStorage.getItem(STORAGE);
    if (saved && LANGS.includes(saved)) return saved;
    const browser = (navigator.language || "en").toLowerCase();
    if (browser.startsWith("zh")) return "zh";
    if (browser.startsWith("ja")) return "ja";
    if (browser.startsWith("fr")) return "fr";
    if (browser.startsWith("de")) return "de";
    return "en";
  }

  let lang = detectLang();
  document.documentElement.lang = lang;
  const locale = LOCALES[lang] || "en-US";
  const index = { zh: 0, ja: 1, fr: 2, de: 3 }[lang];

  function fill(template, values) {
    return template.replace(/\{(\d+)\}/g, (_, n) => values[Number(n) - 1] ?? "");
  }

  function translate(text) {
    if (!text) return text;
    if (lang === "en") return EN_TEMPLATES[text] || text;
    const core = text.replace(/\s+/g, " ").trim();
    if (!core) return text;
    const exact = T[core];
    if (exact) return exact[index];
    for (const [re, outputs] of PATTERNS) {
      const m = core.match(re);
      if (m) {
        return fill(outputs[index], m.slice(1).map((v) => translate(v || "")));
      }
    }
    return text;
  }

  function isSkipped(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    return !el || !el.closest || !!el.closest(SKIP);
  }

  function translateText(node) {
    if (!node.nodeValue || isSkipped(node)) return;
    const raw = node.nodeValue;
    const match = raw.match(/^(\s*)([\s\S]*?)(\s*)$/);
    if (!match) return;
    const core = match[2];
    const next = translate(core);
    if (next !== core && next !== raw) node.nodeValue = match[1] + next + match[3];
  }

  function translateAttr(el, name) {
    const value = el.getAttribute(name);
    if (!value) return;
    const next = translate(value);
    if (next !== value) el.setAttribute(name, next);
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { translateText(root); return; }
    if (root.nodeType !== 1) return;
    if (root.matches && root.matches(SKIP)) return;
    for (const name of ["placeholder", "title", "aria-label", "alt"]) translateAttr(root, name);
    for (const child of root.childNodes) walk(child);
  }

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "characterData") translateText(record.target);
      else if (record.type === "attributes") {
        translateAttr(record.target, record.attributeName);
      } else {
        for (const node of record.addedNodes) walk(node);
      }
    }
  });

  function ready() {
    document.querySelectorAll("select[data-lang-select]").forEach((select) => {
      select.value = lang;
      select.addEventListener("change", () => {
        localStorage.setItem(STORAGE, select.value);
        location.reload();
      });
    });
    document.title = translate(document.title);
    walk(document.body);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label", "alt"],
    });
  }

  window.UNZZZ_I18N = {
    get lang() { return lang; },
    get locale() { return locale; },
    t(key, values) {
      let translated = translate(key);
      if (values) {
        translated = translated.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
      }
      return translated;
    },
    date(ts, opts = {}) {
      return new Intl.DateTimeFormat(locale, opts).format(new Date(ts * 1000));
    },
    weekday(index) {
      const base = new Date(Date.UTC(2024, 0, 1 + Number(index)));
      return new Intl.DateTimeFormat(locale, { weekday: "short", timeZone: "UTC" }).format(base);
    },
    days(alarm) {
      if (alarm.once_date) {
        return fill(translate("Once on {date}"), [
          this.date(new Date(alarm.once_date + "T12:00:00").getTime() / 1000,
            { day: "numeric", month: "short", year: "numeric" }),
        ]);
      }
      const days = alarm.days || [];
      if (!days.length) return translate("Never");
      if (days.length === 7) return translate("Every day");
      if (days.length === 5 && days.every((d) => d >= 1 && d <= 5)) return translate("Weekdays");
      if (days.length === 2 && days.includes(6) && days.includes(7)) return translate("Weekends");
      return days.map((d) => window.UNZZZ_I18N.weekday(d - 1)).join(" ");
    },
    next(ts, nowTs) {
      if (!ts) return translate("not scheduled");
      const delta = Number(ts) - Number(nowTs || Date.now() / 1000);
      if (delta < 60) return translate("in less than a minute");
      if (delta < 3600) return fill(translate("in {n} min"), [Math.round(delta / 60)]);
      if (delta < 86400) {
        const h = Math.floor(delta / 3600), m = Math.round((delta % 3600) / 60);
        return fill(translate("in {h}h {m}m"), [h, m]);
      }
      const days = Math.floor(delta / 86400);
      if (days === 1) return fill(translate("tomorrow at {time}"), [this.time(ts)]);
      const date = this.date(ts, { weekday: "short", day: "numeric", month: "short" });
      return fill(translate("{date} at {time}"), [date, this.time(ts)]);
    },
    time(ts) {
      return this.date(ts, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
    },
    countdown(seconds) {
      const s = Math.max(0, Math.floor(seconds));
      const d = Math.floor(s / 86400);
      const h = Math.floor((s % 86400) / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sec = s % 60;
      if (s <= 0) return translate("any moment now");
      if (d) return fill(translate("in {d}d {h}h"), [d, h]);
      if (h) return fill(translate("in {h}h {m}m"), [h, String(m).padStart(2, "0")]);
      if (m) return fill(translate("in {m}m {s}s"), [m, String(sec).padStart(2, "0")]);
      return fill(translate("in {s}s"), [sec]);
    },
    translate,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
  else ready();
})();
