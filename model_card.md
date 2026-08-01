# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  


Name: MusicMatcher-Beta

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

This recomender provides the top 5 songs in the playlist reprsented by songs.csv. This recomnder assumes mood and genre should be weighted more in preference selection. This recomnder is more for a classroom exploration than for real user experience given it's limitied representation of genres to match and inability for user to implement their own profile. 

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

Songs are scored by giving 2 points for a genre or mood macth, 1 point for accoustisic preference match, and up to one point depending if the energy of the song is an exact match to the desried enegery represented by a numerical value between 0 and 1. These points are added together and the top 5 highest scoring songs are recomended with their point breakdown. I created addition user prfoiles to test for edge cases but most of the core logic for recomendation was not pre built.
## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

The are 17 songs in the catelouge each having id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness. The genres represented are  pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, metal, house, r&b, folk, hip hop, dream pop. The moods represented are happy, chill, intense, relaxed, moody, focused, nostalgic, angry, euphoric, romantic, melancholic, playful, dreamy. 7 songs in the daatset were added by me for more variety. There are infinite genres and moods that could be applied for this recomender but thse songs act as a reasonable sample to include.

Project 4 Update: With the implementaitn of RAG two new songs will be recomneded but are instead pulled from gemeni. While this does not include a google search it does still allow this model to incorporate near limitless songs without having them in the database. 

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

The data works well as a basic recomnder. Common profiles like pop with high energy will get apportiate recomndations. Generally users will probably want genre to have higher pritoity when sorting since genre is the most common classification of songs so the prefernce calculation giving more weight to that matches the intuition. 

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

The biggest issue with is recomnder is its simplicity. Almost every song in the dataset has a unique genre so it gives an unrealsitc equal weight to evrything and only allows songs to be categorized as one genre which is not always true. Additionally there is no way to change the weighting of the preferences a genre or mood match is always plus 2 points compared to the maximum 1 point from the other 2 characteristics. This favors users for consider the most important aspect of song genre or mood, and negelcts users who really want accoustics in song. 

Project 4 Update: The AI is limited by not having google search therefore it can only use the training data already present in the model. This also means it is subject to the biases in that training data which I can not account for.

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

Multiple profiels were tested. One of the edge cases profiles were `{'favorite_genre': 'pop', 'favorite_mood': 'sad', 'target_energy': 0.9, 'likes_acoustic': False}`. This profile tested for strange profile that has contradictory genre and mood where the mood is not representative in the dataset. I was looking to see how preferences would change when a preferenc eis impossible to match and as expected it basically resulted in reliance on the other three characteristics inadvertently giving more weight to genre. Another profile was `{'favorite_genre': 'metal', 'favorite_mood': 'angry', 'target_energy': 1.0, 'likes_acoustic': True}` which shows seeminly contradiciton since high henergy is typically not accoustic. This led to rock songs being recomnded even and the accousticness ends up almost canceled out. Both of these tests show the inherent flaw with the set socring rate for recomendations.

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

The simplicity can be remedied by having user rank the characteristcs by what they want to be prefered most. This way if someone has an extreme preference for accoustics it is less likely to be cancelled out by the other charcteristics. Rankings could also be applied to give multiple chocies for genre or mood to add more nuances to the selection. Adding more songs of both the same and differing genres to what already is present will always be good for a music recomender.

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps 

I learend about the complexity in accomedating a very varied medium of music and how to handle nearly infinite user preferences. I don;t really use music recomndation apps but I am now more appreicative of the work that went into making them. 

## Reliability

Thw ai turned out more reliable than I thought. When I was planning the implementation with claude I was warned that result may vary per run but upon testing it and reviewing the results myself it was consistently give the same results each time.

## AI  Colaboration

Ai was used extensiviely when coding to due to being new with working with ai and implementing it into a program. Afterwards I often asked the ai for summaries of how the code works so I can understand and it in case changes need to be made later. Addtionally sumaries and may git comit messages were done by ai to save on time and ensure thoroughness. These were all manually reviwed in case the AI missed any important details.