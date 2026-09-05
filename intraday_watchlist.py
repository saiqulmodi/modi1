INTRADAY_SYMBOLS = [
    "LLOYDSME", "VMM", "KRBL", "ZAGGLE", "MARUTI", "M&M",
    "HYUNDAI", "LENSKART", "ATULAUTO", "ASTRAL", "BEL", "GLAND",
    "JUBLFOOD", "COALINDIA", "POONAWALLA", "KAJARIACER", "ETERNAL", "GRASIM",
    "VINATIORGA", "APLAPOLLO", "GOKEX", "BHARTIHEXA", "HINDALCO", "STARHEALTH",
    "AHLUCONT", "ADANIPORTS", "MOTHERSON", "SUPRAJIT", "ZFCVINDIA", "MSUMI",
    "ENDURANCE", "ASKAUTOLTD", "ARE&M", "UNOMINDA", "AGARWALEYE", "RATNAVEER",
    "ACE", "JIOFIN", "GRSE", "NORTHARC", "RATEGAIN", "PIDILITIND",
    "AVALON", "SHRIRAMFIN", "UPL", "ICICIGI", "RELIANCE", "SUNFLAG",
    "HINDCOPPER", "NYKAA", "SBIN", "SBILIFE", "ICICIBANK", "SANDUMA",
    "MEESHO", "UNITDSPR", "SAGILITY", "HINDZINC", "CUMMINSIND", "RHIM",
    "SAATVIKGL", "DIVISLAB", "ZYDUSLIFE", "PPLPHARMA", "COHANCE", "ANTHEM",
    "MARKSANS", "NEULANDLAB", "NETWEB", "ANANTRAJ", "TECHNOE",
    "SUPREMEIND", "APOLLOPIPE", "POLYCAB", "CARYSIL", "DELHIVERY", "APOLLO",
    "KALYANKJIL", "GOPAL", "SOMANYCERA", "SONACOMS", "ABB", "ICIL",
    "SIGNATURE", "SANDHAR", "SUNTECK", "BOMDYEING", "AJMERA", "HUDCO",
    "LODHA", "GODREJPROP", "SOBHA", "OBEROIRLTY", "BRIGADE", "DBREALTY",
    "MANKIND", "MOIL", "GMRAIRPORT", "AURIONPRO", "CENTUM", "KEI",
    "BDL", "ROUTE", "PRECWIRE", "SOLARINDS", "TATAPOWER", "ARVINDFASN",
    "OSWALPUMPS", "TAJGVK", "PRESTIGE", "BANSALWIRE", "GULFOILLUB", "HBLENGINE",
    "CEMPRO", "MIDWESTLTD", "ATLANTAELE", "BALUFORGE", "AARTIIND", "AEGISLOG",
    "ZENTEC", "PARAS", "MAZDOCK", "SYRMA", "DATAPATTNS", "COCHINSHIP",
    "HAL", "ASTRAMICRO", "STLTECH", "GRINDWELL", "SANSERA", "WAAREEENER",
    "TIPSMUSIC", "CUPID", "TDPOWERSYS", "MTARTECH", "DIACABS", "AETHER",
    "SHRIPISTON", "VENTIVE", "CENTURYPLY", "KANSAINER", "SUDARSCHEM", "TRIVENI",
    "GNFC", "SRF", "MSTCLTD", "UJJIVANSFB", "GMMPFAUDLR", "BAJAJELEC",
    "JSFB", "MFSL", "RUBICON", "TI", "GPPL", "AZAD", "HAPPSTMNDS", "VOLTAMP",
    "BALAMINES", "VAML", "KIRLOSENG", "AMBUJACEM", "SHILPAMED", "INDIGOPNTS",
    "KIRLPNU", "NEOGEN", "MANORAMA", "GODREJAGRO", "ASTERDM", "BLUESTARCO",
    "CASTROLIND", "CDSL", "ANGELONE", "RADICO", "CAMS", "CHAMBLFERT",
    "CROMPTON", "KARURVYSYA", "CHALET", "MANAPPURAM", "LEMONTREE", "FSL",
    "MCX", "PNBHOUSING", "NATIONALUM", "NAVINFLUOR", "INDHOTEL", "EIHOTEL",
    "ROHLTD", "WELCORP", "RAMCOCEM", "REDINGTON", "KFINTECH", "PGEL",
    "CYIENTDLM", "BBOX", "WABAG", "TRANSRAILL", "ARTEMISMED", "NBCC",
    "JSL", "VTL", "LUMAXTECH", "CRAFTSMAN", "TORNTPOWER", "ADANIENSOL",
    "JSWENERGY", "ADANIGREEN", "NTPC", "POWERGRID", "THYROCARE", "CONCORDBIO",
    "IPCALAB", "NH", "VIJAYA", "ARVIND", "BIOCON", "GRAVITA", "JINDALSAW",
    "ENGINERSIN", "RML", "GARFIBRES", "RAINBOW", "RRKABEL", "CARTRADE",
    "LANDMARK", "ZENSARTECH", "BALKRISIND", "THERMAX", "CLEAN", "IDEAFORGE",
    "ASHOKLEY", "RKFORGE", "IGIL", "GPIL", "KPIL", "SHAKTIPUMP",
    "RVNL", "IRFC", "PFC", "USHAMART", "NMDC", "HONASA", "TARIL", "VSSL",
    "GODREJIND", "SAILIFE", "CEATLTD", "SCHNEIDER", "AADHARHFC", "JKCEMENT",
    "360ONE", "ACMESOLAR", "TEGA", "ELGIEQUIP", "PCBL", "LCL",
    "BEML", "ASAHIINDIA", "SCI", "JARO", "PWL", "VERANDA", 
    "WELSPUNLIV", "KPRMILL", "PERSISTENT", "COFORGE", "INDIGO", "ABCAPITAL",
    "TVSMOTOR", "BAJAJ-AUTO", "TATACOMM", "WINDLAS", "AMRUTANJAN", "PFIZER",
    "ASIANPAINT", "INGERRAND", "WALCHANNAG", "AMAGI", "TITAGARH", "MANIPALHOS", "TATACAP",
    "NAM-INDIA", "EMMVEE", "FINEORG", "GABRIEL", "GRWRHITECH", "ITCHOTELS",
    "JBMA", "MINDACORP", "PRIVISCL", "DMART", "SHYAMMETL", "FMGOETZE",
    "URBANCO", "SUMICHEM", "ZYDUSWELL", "TRAVELFOOD", "SHANTIGEAR",

    # Added from NIFTY 50 + NIFTY Financial Services (official NSE index
    # constituent lists), deduped against the symbols already above.
    "ADANIENT", "APOLLOHOSP", "AXISBANK", "BAJAJFINSV", "BAJFINANCE",
    "BHARTIARTL", "BSE", "CHOLAFIN", "CIPLA", "DRREDDY", "EICHERMOT",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HINDUNILVR", "INFY", "ITC",
    "JSWSTEEL", "KOTAKBANK", "LICHSGFIN", "LT", "MAXHEALTH", "MUTHOOTFIN",
    "NESTLEIND", "ONGC", "RECLTD", "SBICARD", "SUNPHARMA", "TATACONSUM",
    "TATASTEEL", "TCS", "TECHM", "TITAN", "TMPV", "TRENT", "ULTRACEMCO",
    "WIPRO",

    # Pharma/CDMO + hospital: NIFTY Pharma + NIFTY Healthcare (official NSE
    # index lists) plus dedicated CDMO/hospital names from general knowledge
    # (not from an official index -- worth a spot-check).
    "ABBOTINDIA", "AJANTPHARM", "ALKEM", "AUROPHARMA", "FORTIS", "GLENMARK",
    "LAURUSLABS", "LUPIN", "SYNGENE", "TORNTPHARM", "WOCKPHARMA",
    "AARTIPHARM", "HIKAL", "KIMS", "SHALBY",
    "YATHARTH", "MEDANTA",

    # Textiles (general knowledge, not an official index -- worth a spot-check).
    "TRIDENT", "RAYMOND", "PAGEIND", "SUTLEJTEX", "SIYSIL", "NITINSPIN",
    "HIMATSEIDE",

    # Hospitality/travel (general knowledge, not an official index -- worth a spot-check).
    "MHRIL", "SAMHI", "JUNIPER", "EASEMYTRIP", "THOMASCOOK", "WONDERLA",

    # Auto ancillaries: NIFTY Auto (official NSE index, includes OEMs +
    # top ancillaries) plus additional dedicated ancillary names from
    # general knowledge (not from an official index -- worth a spot-check).
    "BHARATFORG", "BOSCHLTD", "EXIDEIND", "HEROMOTOCO", "TIINDIA",
    "APOLLOTYRE", "AUTOAXLES", "FIEMIND", "JAMNAAUTO",
    "LUMAXIND", "MRF", "RAJRATAN", "RANEHOLDIN",
    "RICOAUTO", "SSWL", "SUBROS", "SUNDRMFAST", "VARROC",

    # Data center theme (genuinely niche in listed Indian markets -- most
    # pure-play data center operators aren't public; these are the closest
    # listed proxies, from general knowledge not an official index). SIFY
    # dropped -- it's NASDAQ-listed (ADR) only, not on NSE.
    "RAILTEL", "KAYNES",

    # Construction/housing/railway/bridges + ancillaries (cement, paint,
    # tiles, pipes): NIFTY Realty + NIFTY Infra (official NSE index lists)
    # plus dedicated names from general knowledge (not an official index --
    # worth a spot-check).
    "ABREL", "BPCL", "CGPOWER", "DLF", "GAIL", "HINDPETRO", "INDUSTOWER",
    "IOC", "PHOENIXLTD", "SHREECEM", "SUZLON",
    "ACC", "JSWDULUX", "ASHOKA", "BERGEPAINT", "BIRLACORPN", "CERA",
    "DALBHARAT", "DBL", "FINPIPE", "GRINFRA", "INDIACEM", "IRB", "IRCON",
    "JKIL", "JKLAKSHMI", "KEC", "KNRCON", "NCC", "NITCO",
    "NUVOCO", "ORIENTBELL", "PNCINFRA", "PRINCEPIPE", "RITES",
    "STARCEMENT", "TEXRAIL",

    # Added by explicit request after showing up in MODI3's order-win/
    # results news coverage (JBFIND, CEIGALL, AHLWEST) plus two more asked
    # for directly (PITTIENG, VEDL). JBFIND dropped -- not a real NSE symbol;
    # the intended company (J.B. Chemicals, JBCHEPHARM) has since amalgamated
    # into Torrent Pharma, already on this list as TORNTPHARM.
    "CEIGALL", "AHLWEST", "PITTIENG", "VEDL",

    # Added by explicit request (large batch). A few needed correcting from
    # the names given: MOLDTEKPACK -> MOLDTKPAC, CAPPACIT INFRA -> CAPACITE,
    # TATA TECHNOLOGY -> TATATECH, AIA -> AIAENG, NEPHROCARE -> NEPHROPLUS,
    # IFB -> IFBIND, KIRLOSBRO -> KIRLOSBROS, RAYMONREL -> RAYMONDREL.
    # "JIOFINBELRISE" and "SPALSUMICHEM" were two names run together without
    # a comma -- split into BELRISE (JIOFIN was already on the list) and
    # SPAL + SUMICHEM (SUMICHEM was already on the list) respectively.
    "JKPAPER", "AUBANK", "MAHSEAMLES", "AVANTIFEED", "BASF", "RAIN",
    "MOLDTKPAC", "CAPACITE", "JSWINFRA", "TATATECH", "AIAENG", "BELRISE",
    "ATHERENERG", "NEPHROPLUS", "MANINFRA", "CIEINDIA", "DOMS", "ENRIN",
    "ENTERO", "EPACK", "GVT&D", "HARSHA", "HEG", "HIRECT", "IFBIND",
    "INTELLECT", "KIRLOSBROS", "KRISHANA", "LALPATHLAB", "MAHLIFE",
    "MIDHANI", "POWERMECH", "RAYMONDLSL", "RAYMONDREL", "SAFARI", "SIS",
    "SOUTHBANK", "SPAL", "SKFINDIA", "SJS", "SHANKARA",

    # Added by explicit request. Corrections: STYLAM -> STYLAMIND,
    # PRICOL -> PRICOLLTD. "CP Plus" (CCTV brand) requested but not found
    # listed on NSE at all -- skipped, not guessed.
    "SUPRIYA", "AKUMS", "RAMRAT", "DPABHUSHAN", "NELCAST", "PREMIERENE",
    "VSTTILLERS", "TIMEX", "TENNIND", "CANFINHOME", "J&KBANK", "BANKBARODA",
    "HDFCAMC", "CARRARO", "PSPPROJECT", "TALBROAUTO", "JKTYRE", "GNA",
    "PRICOLLTD", "ESCORTS", "SIRCA", "GOODLUCK", "STYLAMIND", "EPACKPEB",

    # Added by explicit request. TVSMOTOR and WOCKPHARMA already present.
    "MASTEK",

    # Added by explicit request (large batch). Corrections: CESE -> CESC,
    # SURYARROSNI -> SURYAROSNI, "KSOLVESNESTLEIND" was two names run
    # together without a comma -- split into KSOLVES (NESTLEIND already
    # present). "NEWZENSSWL" couldn't be confidently resolved to a real
    # symbol -- skipped rather than guessed (SSWL is already present
    # separately). LEAPIND, VALIANT (real ticker: VALIANTLAB), KRN, DLINK
    # (real ticker: DLINKINDIA), KAPTON (real ticker: KAPSTON), and
    # SUNSHIEL aren't in Motilal's scrip file (dated 09-Aug-2026) but are
    # in Angel's -- see ANGEL_ONLY_SYMBOLS below.
    "CYIENT", "FINCABLES", "SGMART", "MPSLTD", "VIMTALABS", "PAYTM",
    "ROSSARI", "TATVA", "ADANIPOWER", "GROWW", "SAPPHIRE", "GREENPLY",
    "SAKAR", "GESHIP", "CESC", "PNBGILTS", "BHARATRAS", "VENUSPIPES",
    "EMSLIMITED", "GLAXO", "KKCL", "HDBFS", "BAJAJHFL", "BAJAJCON",
    "GRANULES", "HESTERBIO", "OFSS", "MPHASIS", "PARKHOSPS", "SHARDAMOTR",
    "ERIS", "POLICYBZR", "INDIASHLTR", "SHAILY", "BECTORFOOD", "REDTAPE",
    "TCPLPACK", "SURYAROSNI", "TBZ", "KSOLVES",

    # Added by explicit request. Corrections: THEELA -> THELEELA (Schloss
    # Bangalore/The Leela), INDOAMIN-BE -> INDOAMIN (real ticker has no
    # suffix; it's a BE-series/trade-to-trade stock in nse_scrips.csv, not
    # EQ, so it's routed to Angel via ANGEL_ONLY_SYMBOLS below like the
    # other -BE names, rather than Motilal's EQ-only lookup).
    "RALLIS", "NOVARTIND", "CHENNPETRO", "SOLARA", "NTPCGREEN", "GUJALKALI",
    "WIPL", "CAPLIPOINT", "EMCURE", "RATNAMANI", "INDOAMIN", "KPIGREEN",
    "INDIAGLYCO", "SHREEJISPG", "SWARAJENG", "AWL", "PICCADIL", "THELEELA",

    # Added by explicit request (large batch). DATAPATTNS, CUMMINSIND, LT
    # already present, skipped. MENONBE-BE -> MENONBE (BE-series, same
    # handling as INDOAMIN above -- routed to Angel via ANGEL_ONLY_SYMBOLS).
    # HITECK and ICICIGINAV couldn't be confidently resolved to a real
    # symbol (multiple candidates for HITECK, no match for ICICIGINAV --
    # ICICIGI is already present separately) -- skipped rather than guessed.
    "POWERINDIA", "LICI", "PGHL", "IKS", "AURUM", "NAVKARCORP", "MENONBE",
    "RAMAPHO", "HUHTAMAKI", "ARVSMART", "GMDCLTD", "CEINSYS", "HUBTOWN",
    "FDC", "GARUDA", "BORORENEW", "KTKBANK", "SEDEMAC", "ALIVUS", "SARDAEN",
    "EUROPRATIK", "DOLLAR", "RUPA", "THEJO", "BLUEDART", "NIVABUPA",
    "ADFFOODS", "DEVYANI", "TRUALT", "DIXON", "IIFL", "BANKINDIA", "RAMKY",
    "NAZARA", "PIIND", "EMAMILTD", "EUREKAFORB", "MAHABANK", "EPL", "KROSS",
    "SHAREINDIA", "KDDL", "BLS", "MAYURUNIQ", "DREDGECORP", "METROBRAND",
    "PACEDIGITK", "BAYERCROP", "NESCO", "SAGCEM", "MASFIN", "NATCOPHARM",
    "MANGLMCEM", "TAALTECH", "SATIN", "DRAGARWQ", "NOCIL", "UNIMECH",
    "TIMKEN", "SANOFI", "ELANTAS", "IGARASHI", "GOLDIAM", "PDSL", "JGCHEM",
    "MEDIASSIST", "VESUVIUS", "GHCLTEXTIL", "INDIANB", "FEDERALBNK",
    "SERVOTECH", "RPGLIFE", "VENKEYS", "VOLTAS", "ALICON", "IZMO",
    "AJAXENGG", "APARINDS", "LTF", "SMARTWORKS", "ORIENTELEC", "UTIAMC",
    "GANDHAR", "BHAGCHEM", "CAPITALSFB",

    # Added 2026-09-05 at user's request (batch add, ~180 pasted symbols).
    # Every symbol below was verified against live Yahoo Finance price
    # history before being added. A few misspellings from the original
    # paste were corrected to their real ticker (JINDALRILL->JINDRILL,
    # KENNAMETN->KENNAMET, INDIAIANB->INDIANB [already present, so dropped
    # as a duplicate], GODAVERIB->GODAVARIB, RISHABHA->RISHABH, TILL->TIL,
    # CMLLALPINETEX->ALPINETEX). 9 symbols from the paste (ASMTEC, SGGHFL,
    # MOBAVENUE, LGINDIA, AFCOM, NIYOGIN, LAXMIIINDIA, DYNAVSN, LALTHAA)
    # matched no ticker on Yahoo even after correction attempts and were
    # left out rather than guessed. KRT was initially added (matched a
    # loose nse_scrips.csv substring check) but removed after verify_symbols.py
    # + a direct Yahoo check found it has zero price data -- its only NSE
    # listing is "KRT-RR", a temporary Rights Renunciation instrument from
    # a rights issue, not the regular equity. 17 of the remaining symbols
    # aren't in Motilal's nse_scrips.csv (recent listings) but do resolve
    # on Angel One, so they're routed there via ANGEL_ONLY_SYMBOLS below.
    "COLPAL", "CUB", "GODFRYPHLP", "TEAMLEASE", "PTCIL", "STEELCAS",
    "PANAMAPET", "JSWCEMENT", "SKYGOLD", "SAIL", "GATEWAY", "IMFA",
    "RELAXO", "SAMBHV", "HARIOMPIPE", "TEXMOPIPES", "KIOCL", "KSB",
    "SFL", "NAHARSPING", "ROLEXRINGS", "MANYAVAR", "KRISHNADEF", "BANCOINDIA",
    "ZFSTEERING", "RPSGVENT", "RCF", "OBSCP", "UNICHEMLAB", "BOROSCI",
    "GANECOS", "WSTCSTPAPR", "ROSSTECH", "ACCELYA", "BRITANNIA", "ETHOSLTD",
    "HGINFRA", "LTFOODS", "GRAPHITE", "VMARCIND", "GALAXYSURF", "FOSECOIND",
    "SURAKSHA", "TVSSRICHAK", "IREDA", "AKCAPIT", "UNIONBANK", "JMFINANCIL",
    "DSSL", "KITEX", "APTUS", "ACUTAAS", "AEGISVOPAK", "BLUESTONE",
    "THEMISMED", "RPEL", "SHARDACROP", "JUBLINGREA", "CPPLUS", "WHEELS",
    "DMCC", "FCL", "PRECOT", "CLEANMAX", "ECLERX", "BBTC",
    "SOTL", "PATELENG", "THANGAMAYL", "HINDWAREAP", "SANGHVIMOV", "LAOPALA",
    "NGLFINE", "VISHNU", "ABLBL", "CSBBANK", "OMNI", "INDOBORAX",
    "YASHO", "ALLDIGI", "GREAVESCOT", "NRBBEARING", "INDGN", "GODREJCP",
    "TANLA", "LGBBROSLTD", "EMIL", "EDELWEISS", "TRITURBINE", "LINCOLN",
    "BLISSGVS", "BLUEJET", "CREDITACC", "MACPOWER", "ASHAPURMIN", "CORONA",
    "BSOFT", "JAYNECOIND", "POLYMED", "SONATSOFTW", "LATENTVIEW", "JUBLPHARMA",
    "INDORAMA", "CINELINE", "CORDELIA", "INDIQUBE", "KPEL",
    "SWIGGY", "NLCINDIA", "MODIS", "KALPATARU", "METROPOLIS", "WEWORK",
    "ORKLAINDIA", "DHANUKA", "LTM", "INDOMIM", "DATAMATICS", "SJVN",
    "VASCONEQ", "CMLL", "LASERPOWER", "KUSUMGAR", "KISSHT", "HEXAGON",
    "RAMBHAJO", "KNACK", "YOGI", "AUGMONT", "TEMPSENS", "BLEL",
    "SHIPROCKET", "MILKYMIST", "HTEL", "SKYWAYS", "SHANKESH", "DHOOTTRANS",
    "GAJA", "SUNSHINE", "MOLBIO", "JINDRILL", "KENNAMET", "GODAVARIB",
    "RISHABH", "TIL", "ALPINETEX",
]

# Symbols not present as "EQ" in Motilal's nse_scrips.csv -- routed straight to
# Angel One instead of a Motilal scripcode lookup. Value is the Angel symbol
# suffix: "-EQ" normal, "-BE" = trade-to-trade (T2T stocks cannot be squared
# off intraday -- alerts only, no auto-trade logic). ITDCEM (ITD Cementation)
# and RANEBRAKE (Rane Brake Lining) were confirmed missing from BOTH
# nse_scrips.csv and Angel's scrip master as of 2026-08-28 -- Yahoo Finance
# has zero data for either ticker too (confirmed 2026-09-05), so both were
# removed from INTRADAY_SYMBOLS above rather than left in unresolved.
# RANEBRAKE's current NSE symbol is reportedly "RBL" -- not re-added here
# since that hasn't been independently verified.
ANGEL_ONLY_SYMBOLS = {
    "DBREALTY": "-EQ",
    "IDEAFORGE": "-EQ",
    "STLTECH": "-BE",
    "MTARTECH": "-BE",
    "DIACABS": "-BE",
    "SUTLEJTEX": "-BE",
    "AHLWEST": "-BE",
    "INDOAMIN": "-BE",
    "MENONBE": "-BE",
    "KRN": "-EQ",
    "LEAPIND": "-EQ",
    "SUNSHIEL": "-EQ",
    "VALIANTLAB": "-EQ",
    "DLINKINDIA": "-EQ",
    "KAPSTON": "-EQ",

    # Added 2026-09-05 with the batch-add above -- recent listings not yet
    # in Motilal's nse_scrips.csv snapshot but confirmed present in Angel's
    # scrip master (re-downloaded 2026-09-05 to check). OBSCP and VMARCIND
    # trade on the NSE SME board ("-SM", not "-EQ"/"-BE") -- lower liquidity
    # than mainboard names, worth keeping in mind for alert sizing.
    "BLISSGVS": "-BE",
    "HEXAGON": "-BE",
    "HTEL": "-BE",
    "YOGI": "-EQ",
    "AUGMONT": "-EQ",
    "TEMPSENS": "-EQ",
    "BLEL": "-EQ",
    "SHIPROCKET": "-EQ",
    "MILKYMIST": "-EQ",
    "SKYWAYS": "-EQ",
    "SHANKESH": "-EQ",
    "DHOOTTRANS": "-EQ",
    "GAJA": "-EQ",
    "SUNSHINE": "-EQ",
    "MOLBIO": "-EQ",
    "OBSCP": "-SM",
    "VMARCIND": "-SM",
}