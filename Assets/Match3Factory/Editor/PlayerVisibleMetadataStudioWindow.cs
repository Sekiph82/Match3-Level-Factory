using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace Match3Factory
{
    public sealed class PlayerVisibleMetadataStudioWindow : EditorWindow
    {
        private static readonly string[] Profiles = GameProfileCatalog.AllProfileIds.ToArray();
        private PlayerVisibleMetadataDraft metadata = new PlayerVisibleMetadataDraft();
        private VisualElement root;

        [MenuItem("Tools/Match3 Factory/Player-visible Metadata")]
        public static void Open()
        {
            var window = GetWindow<PlayerVisibleMetadataStudioWindow>();
            window.titleContent = new GUIContent("Player Metadata");
            window.minSize = new Vector2(620, 520);
        }

        public void CreateGUI() => Build();

        private void Build()
        {
            rootVisualElement.Clear();
            root = rootVisualElement;
            root.style.paddingLeft = 12; root.style.paddingRight = 12;
            root.style.paddingTop = 10; root.style.paddingBottom = 10;
            var title = new Label("Player-visible campaign metadata · schema v1 · DATA ONLY");
            title.style.unityFontStyleAndWeight = FontStyle.Bold;
            root.Add(title);
            root.Add(new HelpBox("This editor stores teaser, progress, journey, chest, collection and explicitly sourced expiry metadata. It does not grant rewards, calculate progress, or establish Engine compatibility.", HelpBoxMessageType.Info));

            var actions = new VisualElement { style = { flexDirection = FlexDirection.Row } };
            actions.Add(Button("Open JSON", OpenJson));
            actions.Add(Button("Save JSON", SaveJson));
            actions.Add(Button("Validate", ShowValidation));
            root.Add(actions);
            var profile = new DropdownField("Game profile", Profiles.ToList(), Math.Max(0, Array.IndexOf(Profiles, metadata.gameProfileId)));
            profile.RegisterValueChangedCallback(evt => metadata.gameProfileId = evt.newValue); AddField(profile);
            AddField(TextInput("Next-level teaser key", metadata.nextLevelTeaserKey, value => metadata.nextLevelTeaserKey = value));
            AddField(TextInput("Chapter progress label key", metadata.chapterProgressLabelKey, value => metadata.chapterProgressLabelKey = value));
            AddField(IntegerInput("Journey length (schema v1 fixed at 10)", metadata.journeyLevelCount, value => metadata.journeyLevelCount = value));

            root.Add(new Label("Earned chest / star milestones (display metadata only)"));
            var milestones = new VisualElement(); root.Add(milestones);
            BuildMilestones(milestones);
            root.Add(Button("Add chest milestone", () => { metadata.chestMilestones = (metadata.chestMilestones ?? Array.Empty<ChestMilestoneMetadata>()).Concat(new[] { new ChestMilestoneMetadata { milestoneId = "milestone.new", atLevel = 10, starThreshold = 1, displayLabelKey = "chest.milestone" } }).ToArray(); Build(); }));

            root.Add(new Label("Collection items and packs (catalog display data only)"));
            var items = new VisualElement(); root.Add(items);
            BuildItems(items);
            root.Add(Button("Add collection item", () => { metadata.collectionItems = (metadata.collectionItems ?? Array.Empty<CollectionItemMetadata>()).Concat(new[] { new CollectionItemMetadata { itemId = "collection.item", packId = "collection.pack", displayLabelKey = "collection.item.label" } }).ToArray(); Build(); }));

            root.Add(new Label("Expiry disclosure (all fields required together; never inferred)"));
            AddField(TextInput("Expiry UTC (yyyy-MM-ddTHH:mm:ssZ)", metadata.expiryUtc, value => metadata.expiryUtc = value));
            AddField(TextInput("Expiry source reference", metadata.expirySourceReference, value => metadata.expirySourceReference = value));
            AddField(TextInput("Expiry disclosure localization key", metadata.expiryDisclosureKey, value => metadata.expiryDisclosureKey = value));
        }

        private void BuildMilestones(VisualElement parent)
        {
            var values = metadata.chestMilestones ?? Array.Empty<ChestMilestoneMetadata>();
            for (int i = 0; i < values.Length; i++)
            {
                int index = i; var item = values[i];
                var row = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
                row.Add(TextInput("ID", item.milestoneId, value => item.milestoneId = value));
                row.Add(IntegerInput("Level", item.atLevel, value => item.atLevel = value));
                row.Add(IntegerInput("Stars", item.starThreshold, value => item.starThreshold = value));
                row.Add(TextInput("Label key", item.displayLabelKey, value => item.displayLabelKey = value));
                row.Add(Button("Remove", () => { metadata.chestMilestones = values.Where((_, position) => position != index).ToArray(); Build(); }));
                parent.Add(row);
            }
        }

        private void BuildItems(VisualElement parent)
        {
            var values = metadata.collectionItems ?? Array.Empty<CollectionItemMetadata>();
            for (int i = 0; i < values.Length; i++)
            {
                int index = i; var item = values[i];
                var row = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
                row.Add(TextInput("Item ID", item.itemId, value => item.itemId = value));
                row.Add(TextInput("Pack ID", item.packId, value => item.packId = value));
                row.Add(TextInput("Label key", item.displayLabelKey, value => item.displayLabelKey = value));
                row.Add(Button("Remove", () => { metadata.collectionItems = values.Where((_, position) => position != index).ToArray(); Build(); }));
                parent.Add(row);
            }
        }

        private void AddField(VisualElement field) => root.Add(field);
        private static Button Button(string label, Action action) => new Button(action) { text = label, tooltip = label };
        private static TextField TextInput(string label, string value, Action<string> changed)
        {
            var field = new TextField(label) { value = value ?? string.Empty };
            field.RegisterValueChangedCallback(evt => changed(evt.newValue));
            return field;
        }
        private static IntegerField IntegerInput(string label, int value, Action<int> changed)
        {
            var field = new IntegerField(label) { value = value };
            field.RegisterValueChangedCallback(evt => changed(evt.newValue));
            return field;
        }

        private void ShowValidation()
        {
            var errors = metadata.Validate();
            EditorUtility.DisplayDialog(errors.Count == 0 ? "Metadata valid" : "Metadata needs correction",
                errors.Count == 0 ? "Versioned local metadata is valid. No reward or Engine behavior was executed." : string.Join("\n", errors), "OK");
        }

        private void OpenJson()
        {
            string path = EditorUtility.OpenFilePanel("Open player metadata", "Assets/Match3Factory/Metadata", "json");
            if (string.IsNullOrEmpty(path)) return;
            try { metadata = PlayerVisibleMetadataDraft.FromJson(File.ReadAllText(path)); Build(); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Open failed", ex.Message, "OK"); }
        }

        private void SaveJson()
        {
            var errors = metadata.Validate();
            if (errors.Count != 0) { EditorUtility.DisplayDialog("Save blocked", string.Join("\n", errors), "OK"); return; }
            string path = EditorUtility.SaveFilePanel("Save player metadata", "Assets/Match3Factory/Metadata", "campaign-metadata", "json");
            if (string.IsNullOrEmpty(path)) return;
            if (File.Exists(path) && !EditorUtility.DisplayDialog("Replace metadata?", "The selected JSON already exists. Replace it?", "Replace", "Cancel")) return;
            try { File.WriteAllText(path, metadata.ToJson() + "\n", new System.Text.UTF8Encoding(false)); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Save failed", ex.Message, "OK"); }
        }
    }
}
