<saved-search>
<ul class="savedsearch-list">
  <li class="savedsearch-info" each={ items }>
    <a class="query" href="https://twitter.com/search?src=typd&q={ encodeURIComponent(query) }">{ name }</a>
    <span class="timestamp">{ timestamp }</span>
    <span class="remove" id="{ id }" onclick={ parent.remove }>
      <a class="delete is-small"></a>
    </span>
  </li>
</ul>

<script>
var self = this;

fetch('api/saved_searches/list')
.then(function(data) {
  return data.json();
})
.then(function(json) {
  self.items = json;
  self.update();
})
.catch(function(err) {
  console.error(err);
})

remove(event) {
  var id = event.item.id;
  var request = new Request('api/saved_search/destroy/' + id, {
    method: 'DELETE'
  });
  fetch(request).then(function(data){console.log(data)})
  var item = event.item
  var index = this.items.indexOf(item)
  this.items.splice(index, 1)
}
</script>
</saved-search>
